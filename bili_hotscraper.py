# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import time
import json

def scrape_douban_top250():
    """
    爬取豆瓣电影Top 250的所有电影信息。
    
    :return: 包含所有电影信息的列表 (list of dict)
    """
    
    base_url = "https://movie.douban.com/top250"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_movies = []
    
    for start_num in range(0, 250, 25):
        url = f"{base_url}?start={start_num}"
        print(f"正在爬取豆瓣 Top {start_num+1}-{start_num+25} 的电影...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            movie_items = soup.find_all('div', class_='item')
            
            for item in movie_items:
                # 排名
                # --- 这是我们修改的地方 ---
                rank = item.find('em').get_text()
                
                # 电影标题
                title = item.find('span', class_='title').get_text()
                
                # 电影链接
                link = item.find('div', class_='hd').a['href']
                
                # 电影评分
                rating = item.find('span', class_='rating_num').get_text()
                
                # 电影引言
                quote_tag = item.find('span', class_='inq')
                quote = quote_tag.get_text() if quote_tag else "无"
                
                movie_info = {
                    "rank": rank,
                    "title": title,
                    "rating": rating,
                    "quote": quote,
                    "link": link
                }
                all_movies.append(movie_info)

            time.sleep(1) 

        except requests.exceptions.RequestException as e:
            print(f"请求页面失败: {url}, 错误: {e}")
            continue
    
    print("所有页面爬取完毕！")
    return all_movies


if __name__ == "__main__":
    douban_top250 = scrape_douban_top250()
    
    if douban_top250:
        print("\n" + "="*60)
        print("🎬 豆瓣电影 Top 250 榜单 🎬")
        print("="*60 + "\n")
        
        for movie in douban_top250:
            print(f"【No.{movie['rank']}】《{movie['title']}》 - 评分: {movie['rating']}")
            print(f"  经典引言: {movie['quote']}")
            print(f"  详情链接: {movie['link']}\n")
            
        # 也可以将结果保存到文件
        # with open('douban_top250.json', 'w', encoding='utf-8') as f:
        #     json.dump(douban_top250, f, ensure_ascii=False, indent=4)
        # print("结果已保存到 douban_top250.json 文件。")