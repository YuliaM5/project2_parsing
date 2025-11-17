#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import argparse


def parse_news(url):
    """Парсит новости с указанного URL и группирует их по разделам"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        news_by_section = {}

        if 'iz.ru' in url:
            news_by_section = parse_iz(soup, url)
        else:
            news_by_section = parse_universal(soup, url)

        return news_by_section

    except requests.RequestException as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return {}
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return {}


def parse_iz(soup, base_url):
    """Парсинг специфичный для Iz.ru"""
    news_by_section = {}

    news_items = soup.find_all('div', class_=['lenta_news__item', 'news', 'news-item'])

    if not news_items:
        news_links = soup.find_all('a', href=lambda x: x and ('/news/' in x or '/document/' in x))
        for link in news_links:
            title = link.get_text(strip=True)
            if title and len(title) > 15:
                section = determine_section_by_title(title)
                if section not in news_by_section:
                    news_by_section[section] = []

                full_url = urljoin(base_url, link['href'])
                news_by_section[section].append({
                    'title': title,
                    'url': full_url
                })

    if not news_by_section:
        containers = soup.find_all(['div', 'li'],
                                   class_=lambda x: x and any(word in x for word in ['news', 'item', 'lenta']))
        for container in containers:
            title_elem = container.find(['a', 'h2', 'h3', 'h4'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href')

                if title and len(title) > 15 and link:
                    section = determine_section_by_title(title)
                    if section not in news_by_section:
                        news_by_section[section] = []

                    full_url = urljoin(base_url, link)
                    news_by_section[section].append({
                        'title': title,
                        'url': full_url
                    })

    if not news_by_section:
        return parse_iz_aggressive(soup, base_url)

    return news_by_section


def parse_iz_aggressive(soup, base_url):
    """Агрессивный парсинг для архивной версии Iz.ru"""
    news_by_section = {}

    all_links = soup.find_all('a', href=True)

    for link in all_links:
        href = link['href']
        title = link.get_text(strip=True)

        is_news_link = (
                ('/news/' in href or '/document/' in href) and
                title and
                len(title) > 20 and
                not any(word in title.lower() for word in ['читать далее', 'подробнее', 'смотреть'])
        )

        if is_news_link:
            section = determine_section_by_title(title)

            if section not in news_by_section:
                news_by_section[section] = []

            full_url = urljoin(base_url, href)
            news_by_section[section].append({
                'title': title,
                'url': full_url
            })

    return news_by_section


def parse_universal(soup, base_url):
    """Универсальный парсинг для неизвестных сайтов"""
    news_by_section = {}

    news_selectors = [
        'article',
        '.news-item',
        '.news',
        '.item-news',
        '[class*="news"]',
        '[class*="item"]',
        '.card',
        '.post'
    ]

    for selector in news_selectors:
        items = soup.select(selector)
        for item in items:
            title_elem = item.find(['a', 'h1', 'h2', 'h3', 'h4'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href')

                if title and len(title) > 15 and link:
                    section = determine_section_by_title(title)

                    if section not in news_by_section:
                        news_by_section[section] = []

                    full_url = urljoin(base_url, link)
                    news_by_section[section].append({
                        'title': title,
                        'url': full_url
                    })

    return news_by_section


def determine_section_by_title(title):
    """Определяет раздел по ключевым словам в заголовке"""
    title_lower = title.lower()

    if any(word in title_lower for word in
           ['футбол', 'хоккей', 'спорт', 'матч', 'олимпи', 'чемпионат', 'сборная', 'игр']):
        return 'Спорт'
    elif any(word in title_lower for word in
             ['здоров', 'медицин', 'врач', 'болезн', 'вирус', 'ковид', 'вакцин', 'больни', 'лечен']):
        return 'Здоровье'
    elif any(word in title_lower for word in
             ['политик', 'правительств', 'президент', 'министр', 'госдум', 'выбор', 'власт', 'путин']):
        return 'Политика'
    elif any(word in title_lower for word in
             ['экономик', 'финанс', 'бизнес', 'рынок', 'доллар', 'рубл', 'инфляц', 'цен', 'компани']):
        return 'Экономика'
    elif any(word in title_lower for word in
             ['культур', 'искусств', 'кино', 'театр', 'музык', 'выставк', 'концерт', 'фильм']):
        return 'Культура'
    elif any(word in title_lower for word in
             ['общест', 'город', 'регион', 'власт', 'транспорт', 'дорог', 'школ', 'образовани', 'москв']):
        return 'Общество'
    elif any(word in title_lower for word in ['технолог', 'интернет', 'смартфон', 'компьютер', 'искусс', 'интеллект']):
        return 'Технологии'
    elif any(word in title_lower for word in ['арми', 'воен', 'оборон', 'нато', 'украин', 'сири', 'конфликт']):
        return 'Армия'

    return 'Общие новости'


def print_news(news_by_section):
    """Выводит новости в удобочитаемом формате"""
    if not news_by_section:
        print("Новости не найдены")
        return

    total_news = sum(len(news) for news in news_by_section.values())
    print(f"Всего найдено новостей: {total_news}")

    for section, news_list in news_by_section.items():
        print(f"\n{'=' * 60}")
        print(f"{section.upper()} ({len(news_list)} новостей)")
        print(f"{'=' * 60}")

        for i, news in enumerate(news_list, 1):
            print(f"{i}. {news['title']}")
            print(f"   {news['url']}")


def save_to_json(news_by_section, filename='news.json'):
    """Сохраняет новости в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(news_by_section, f, ensure_ascii=False, indent=2)
    print(f"Новости сохранены в файл: {filename}")


def main():
    """Основная функция программы"""
    parser = argparse.ArgumentParser(description='Парсер новостей')
    parser.add_argument('url', nargs='?', default='https://web.archive.org/web/20230903112115/https://iz.ru/news',
                        help='URL для парсинга (по умолчанию: архив Iz.ru)')
    parser.add_argument('-o', '--output', default='news.json',
                        help='Имя файла для сохранения результатов')

    args = parser.parse_args()

    print(f"Парсим новости с: {args.url}")

    news_by_section = parse_news(args.url)

    print_news(news_by_section)

    if news_by_section:
        save_to_json(news_by_section, args.output)
        print(f"Всего разделов: {len(news_by_section)}")
        total_news = sum(len(news) for news in news_by_section.values())
        print(f"Всего новостей: {total_news}")
    else:
        print("Новости не найдены.")


if __name__ == "__main__":
    main()