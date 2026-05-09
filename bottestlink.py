import os
import time
import re
import json
import hashlib
import traceback
from github import Github, Auth
from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= CẤU HÌNH CƠ BẢN =================
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN") 
GITHUB_REPO_NAME = "uranus6781/caolai" 
GITHUB_FILE_PATH = "playlist.json"
BACKGROUND_IMG = "https://imgur.com/HDRH6Ii"
# ===================================================

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_m3u8_link(driver, url):
    del driver.requests
    driver.get(url)
    max_wait_time = 15
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        for req in driver.requests:
            if req.response and '.m3u8' in req.url:
                if 'chunklist' not in req.url and 'ad' not in req.url:
                    return req.url
        time.sleep(1)
    return "http://waiting.m3u8"

def make_absolute_url(url):
    if not url: return BACKGROUND_IMG
    if url.startswith("//"): return "https:" + url
    if url.startswith("/"): return "https://sv2.hoiquan3.live" + url
    return url

def main():
    driver = init_driver()
    du_lieu_json = {
        "id": "hoiquan-tv-pro",
        "url": f"https://raw.githack.com/{GITHUB_REPO_NAME}/main/{GITHUB_FILE_PATH}",
        "name": "Trực Tiếp Bóng Đá",
        "color": "#1cb57a",
        "grid_number": 3,
        "image": {"type": "cover", "url": "https://i.postimg.cc/02tKjcyN/JT3IVCOJDKW3PBRFZAZUILENLU.jpg"},
        "groups": []
    }

    live_channels = []
    upcoming_channels = []
    link_da_quet = set()

    try:
        wait = WebDriverWait(driver, 15)
        driver.get("https://sv2.hoiquan3.live/lich-thi-dau/bong-da")
        items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
        
        matches_data = []

        for item in items:
            link = item.get_attribute("href")
            if link in link_da_quet: continue
            link_da_quet.add(link)
            
            text = item.text
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if not lines: continue
            
            giai_dau = lines[0].upper()
            teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
            if len(teams) < 2: continue
            doi_1, doi_2 = teams[0].text.strip(), teams[1].text.strip()

            html_content = item.get_attribute("innerHTML")
            all_urls = re.findall(r'src="([^"]+)"', html_content) + re.findall(r'url\([\'"]?(.*?)[\'"]?\)', html_content)
            real_logos = [make_absolute_url(u) for u in all_urls if "bg-fixture" not in u and "data:image" not in u]
            real_logos = list(dict.fromkeys(real_logos))
            
            logo_1 = real_logos[0] if len(real_logos) > 0 else BACKGROUND_IMG
            logo_2 = real_logos[1] if len(real_logos) > 1 else logo_1

            score_match = re.search(r"(\d+)\s*-\s*(\d+)", text)
            ti_so = f"{score_match.group(1)} - {score_match.group(2)}" if score_match else "0 - 0"

            time_match = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})?", text)
            thoi_gian = f"{time_match.group(1)} {time_match.group(2) if time_match and time_match.group(2) else ''}".strip() if time_match else "Đang cập nhật"

            text_upper = text.upper()
            is_finished = any(x in text_upper for x in ["FT", "KT", "HẾT GIỜ"])
            is_live = (bool(score_match) and not is_finished) or (("LIVE" in text_upper or "ĐANG ĐÁ" in text_upper) and not is_finished)

            if not is_finished:
                matches_data.append({
                    "link": link, "giai": giai_dau, "doi_1": doi_1, "doi_2": doi_2,
                    "logo_1": logo_1, "logo_2": logo_2, "ti_so": ti_so,
                    "thoi_gian": thoi_gian, "is_live": is_live
                })

        for tran in matches_data:
            link_m3u8 = get_m3u8_link(driver, tran['link']) if tran['is_live'] else "http://waiting.m3u8"
            tran['m3u8_final'] = link_m3u8 # Lưu lại để dùng cho M3U
            
            nhan_hien_thi = f"🔴 LIVE | {tran['thoi_gian']}" if tran['is_live'] else f"⏳ Sắp diễn ra | {tran['thoi_gian']}"
            label_color = "#e50914" if tran['is_live'] else "#1cb57a"
            match_id = "hq-" + hashlib.md5(f"{tran['doi_1']}{tran['doi_2']}".encode()).hexdigest()[:8]
            
            kenh_json = {
                "id": match_id,
                "name": f"🏆 {tran['giai']} | ⚽ {tran['doi_1']} vs {tran['doi_2']}",
                "type": "single",
                "display": "default",
                "enable_detail": False,  
                "image": {"display": "cover", "url": BACKGROUND_IMG, "width": 1600, "height": 900},
                "labels": [{"text": nhan_hien_thi, "position": "top-left", "color": label_color, "text_color": "#ffffff"}],
                "sources": [{
                    "id": f"src-{match_id}",
                    "name": "Nguồn Phóng",
                    "contents": [{
                        "id": f"ct-{match_id}",
                        "name": f"{tran['doi_1']} vs {tran['doi_2']}",
                        "streams": [{
                            "id": f"st-{match_id}",
                            "name": "Server Siêu Mượt",
                            "stream_links": [{
                                "id": f"lnk-{match_id}",
                                "name": "Bấm Để Xem",
                                "type": "hls",
                                "default": True,
                                "url": link_m3u8,
                                "request_headers": [
                                    {"key": "Referer", "value": "https://sv2.hoiquan3.live"},
                                    {"key": "User-Agent", "value": "Mozilla/5.0"}
                                ]
                            }]
                        }]
                    }]
                }]
            }

            if tran['is_live']: live_channels.append(kenh_json)
            else: upcoming_channels.append(kenh_json)

        if live_channels:
            du_lieu_json["groups"].append({"id": "group-live", "name": "🔴 ĐANG DIỄN RA", "display": "vertical", "channels": live_channels})
        if upcoming_channels:
            du_lieu_json["groups"].append({"id": "group-upcoming", "name": "⏳ SẮP DIỄN RA", "display": "vertical", "channels": upcoming_channels})

        # --- BƯỚC XUẤT FILE ---
        # 1. Xuất football.json
        with open("football.json", "w", encoding="utf-8") as f:
            json.dump(du_lieu_json, f, ensure_ascii=False, indent=4)
        
        # 2. Xuất football.m3u
        m3u_content = "#EXTM3U\n"
        for tran in matches_data:
            group = "LIVE NOW" if tran['is_live'] else "UPCOMING"
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo_1"]}" group-title="{group}", {tran["doi_1"]} vs {tran["doi_2"]} ({tran["giai"]})\n'
            m3u_content += f'{tran["m3u8_final"]}|Referer=https://sv2.hoiquan3.live&User-Agent=Mozilla/5.0\n'
        
        with open("football.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)

        # BƯỚC 3: ĐẨY LÊN GITHUB
        if GITHUB_TOKEN:
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(GITHUB_REPO_NAME)
            json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
            try:
                contents = repo.get_contents(GITHUB_FILE_PATH)
                repo.update_file(contents.path, "Update playlist", json_content, contents.sha)
            except:
                repo.create_file(GITHUB_FILE_PATH, "Create playlist", json_content)

    except Exception:
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
