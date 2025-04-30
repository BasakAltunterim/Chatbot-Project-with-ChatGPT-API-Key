import requests
from bs4 import BeautifulSoup
import json
import os
import schedule
import time


ANNOUNCEMENTS_BASE_URL = "https://www.mehmetakif.edu.tr/tr/contents/35"
EVENTS_BASE_URL = "https://www.mehmetakif.edu.tr/tr/contents/46"
ACADEMIC_STAFF_URL = "https://bbbf.mehmetakif.edu.tr/tr/content/17350/akademik-personel"

def fetch_page_content(url):
    """URL'den sayfa içeriğini alır."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Hata: {url} sayfası alınamadı. Hata: {e}")
        return None

def parse_announcement(announcement):
    """Bir duyuruyu ayrıştırır."""
    try:
        title_tag = announcement.find("a", class_="text-left font-thin text-white")
        date_tag = announcement.find("div", class_="flex flex-row gap-2 flex-1 text-left text-xs text-slate-400")

        if title_tag and date_tag:
            title = title_tag.text.strip()
            raw_date = date_tag.text.strip()
            link = f"https://www.mehmetakif.edu.tr{title_tag['href']}"
            description = fetch_announcement_details(link)

            return {
                "type": "announcement",
                "title": title,
                "date": raw_date,
                "link": link,
                "description": description,
            }
    except AttributeError:
        return None

def fetch_announcement_details(url):
    """Duyuru detaylarını alır."""
    soup = fetch_page_content(url)
    if soup:
        description_div = soup.find("div", class_="col-span-12")
        if description_div:
            return description_div.text.strip()
    return "Açıklama bulunamadı."

def fetch_announcements(num_pages=7):
    """Duyuruları çeker."""
    announcements = []
    for page in range(1, num_pages + 1):
        url = ANNOUNCEMENTS_BASE_URL if page == 1 else f"{ANNOUNCEMENTS_BASE_URL}/{page}/-"
        soup = fetch_page_content(url)
        if not soup:
            continue

        announcement_divs = soup.find_all("div", class_="flex-1 flex flex-col gap-4 text-slate-600 pb-5 px-5")
        for div in announcement_divs:
            announcement = parse_announcement(div)
            if announcement:
                announcements.append(announcement)

    return announcements

def parse_event(event):
    """Bir etkinliği ayrıştırır."""
    try:
        title = event.find("a", class_="text-justify text-slate-700 font-semibold").text.strip()
        link = f"https://www.mehmetakif.edu.tr{event.find('a')['href']}"
        date = event.find("div", class_="flex flex-row gap-2 flex-1 text-left text-xs text-slate-400").text.strip()
        time_info = event.find_all("div", class_="flex flex-row gap-2 flex-1 text-left text-xs text-slate-400")[1].text.strip()
        location = event.find("p").text.strip()

        return {
            "type": "event",
            "title": title,
            "date": date,
            "time": time_info,
            "location": location,
            "link": link,
        }
    except AttributeError:
        return None

def fetch_events(num_pages=7):
    """Etkinlikleri çeker."""
    events = []
    for page in range(1, num_pages + 1):
        url = EVENTS_BASE_URL if page == 1 else f"{EVENTS_BASE_URL}/{page}/-"
        soup = fetch_page_content(url)
        if not soup:
            continue

        container = soup.find("div", class_="mt-10 gap-5 h-full text-slate-500 grid grid-cols-1 md:grid-cols-2")
        if not container:
            continue

        event_divs = container.find_all("div", class_="flex-1 flex flex-col gap-2 items-start")
        for div in event_divs:
            event = parse_event(div)
            if event:
                events.append(event)

    return events

def parse_academic_info(person):
    """Bir akademik personelin bilgilerini ayrıştırır."""
    try:
        name = person.find("div", class_="font-bold").text.strip()
        mail = person.find("div", class_="text-[11px]").text.strip() if person.find("div", class_="text-[11px]") else "E-posta bulunamadı"

        return {
            "type": "academic_staff",
            "name": name,
            "mail": mail,
        }
    except AttributeError:
        return None

def fetch_academic_staff_info():
    """Akademik personel bilgilerini çeker."""
    soup = fetch_page_content(ACADEMIC_STAFF_URL)
    if not soup:
        return []

    container = soup.find("div", class_="flex flex-col gap-5")
    if not container:
        print("Ana container bulunamadı.")
        return []

    staff_info = []
    staff_divs = container.find_all("div", class_="w-full")
    for person in staff_divs:
        info = parse_academic_info(person)
        if info:
            staff_info.append(info)

    return staff_info

def prepare_data_for_fine_tuning(data):
    """Verileri OpenAI fine-tuning formatına dönüştürür."""
    formatted_data = []
    for entry in data:
        if entry["type"] == "announcement":
            formatted_data.append({
                "messages": [
                    {"role": "system", "content": "This is an announcement data."},
                    {"role": "user", "content": f"What's the announcement about {entry['title']}?"},
                    {"role": "assistant", "content": f"Title: {entry['title']}, Date: {entry['date']}, Link: {entry['link']}, Description: {entry['description']}"}
                ]
            })
        elif entry["type"] == "event":
            formatted_data.append({
                "messages": [
                    {"role": "system", "content": "This is an event data."},
                    {"role": "user", "content": f"Tell me about the event {entry['title']}?"},
                    {"role": "assistant", "content": f"Title: {entry['title']}, Date: {entry['date']}, Time: {entry['time']}, Location: {entry['location']}, Link: {entry['link']}"}
                ]
            })
        elif entry["type"] == "academic_staff":
            formatted_data.append({
                "messages": [
                    {"role": "system", "content": "This is an academic staff data."},
                    {"role": "user", "content": f"Who is {entry['name']}?"},
                    {"role": "assistant", "content": f"Name: {entry['name']}, Email: {entry['mail']}"}
                ]
            })
    return formatted_data

def load_existing_data(filename="utils/data.jsonl"):
    """Mevcut verileri JSONL dosyasından yükler."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return [json.loads(line) for line in file]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data_to_jsonl(data, filename="utils/fine_tuning_data.jsonl"):
    """Verileri JSONL dosyasına kaydeder."""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as file:
            for entry in data:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"Veriler {filename} dosyasına kaydedildi.")
    except IOError as e:
        print(f"Hata: Veriler dosyaya kaydedilemedi. Hata: {e}")

def update_data():
    """Yeni duyuru, etkinlik ve akademik personel bilgilerini kontrol eder ve dosyaya kaydeder."""
    print("Duyurular, etkinlikler ve akademik personel bilgileri kontrol ediliyor...")
    new_announcements = fetch_announcements()
    new_events = fetch_events()
    new_academic_staff = fetch_academic_staff_info()
    all_new_data = new_announcements + new_events + new_academic_staff

    if not all_new_data:
        print("Hiçbir yeni veri bulunamadı.")
        return

    existing_data = load_existing_data()

    
    updated_data = {json.dumps(entry, ensure_ascii=False) for entry in existing_data}
    for entry in all_new_data:
        entry_json = json.dumps(entry, ensure_ascii=False)
        if entry_json not in updated_data:
            updated_data.add(entry_json)

    unique_data = [json.loads(entry) for entry in updated_data]
    fine_tuning_data = prepare_data_for_fine_tuning(unique_data)
    save_data_to_jsonl(fine_tuning_data, filename="utils/fine_tuning_data.jsonl")

def main():
    """Ana fonksiyon."""
    print("Duyurular, etkinlikler ve akademik personel bilgileri çekiliyor...")
    update_data()

    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()