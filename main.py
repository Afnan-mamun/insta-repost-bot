import os
import csv
import instaloader
import instabot
import time
import shutil
from datetime import datetime

# --- কনফিগারেশন ---
TARGET_PROFILE = 'voidstomper'  # যে প্রোফাইল থেকে সেরা ভিডিও ডাউনলোড করতে চান
LOG_FILE = 'log.csv'
POST_COUNT_TO_CHECK = 50 # সেরা কতগুলো পোস্টের মধ্যে চেক করতে চান

# --- প্রয়োজনীয় ফাইল তৈরি করা ---
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['shortcode', 'processed_date']) # লগ ফাইলের হেডার

# --- ইন্সটাগ্রামে ভিডিও আপলোড করার ফাংশন ---
def upload_to_instagram(video_path, caption):
    """instabot ব্যবহার করে এই ফাংশনটি ইন্সটাগ্রামে ভিডিও আপলোড করবে।"""
    print(f"ভিডিওটি '{video_path}' ইন্সটাগ্রামে আপলোড করা হচ্ছে...")
    if os.path.exists("config"):
        shutil.rmtree("config")

    bot = instabot.Bot()
    uploader_username = os.environ.get('UPLOADER_INSTA_USER')
    uploader_password = os.environ.get('UPLOADER_INSTA_PASS')

    if not uploader_username or not uploader_password:
        print("ত্রুটি: আপলোড করার অ্যাকাউন্টের ইউজারনেম/পাসওয়ার্ড পাওয়া যায়নি।")
        return False

    bot.login(username=uploader_username, password=uploader_password)
    success = bot.upload_video(video_path, caption=caption)
    bot.logout()

    if success:
        print("সফলভাবে ইন্সটাগ্রামে আপলোড হয়েছে।")
        return True
    else:
        print("ব্যর্থ: ইন্সটাগ্রামে আপলোড করা যায়নি।")
        return False

# --- মূল ফাংশন ---
def main():
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} তারিখে বট চালু হলো ---")

    # ডাউনলোডের জন্য ইন্সটাগ্রামে লগইন
    L = instaloader.Instaloader(download_videos=True, download_geotags=False, 
                                download_comments=False, save_metadata=False)
    try:
        downloader_username = os.environ.get('DOWNLOADER_INSTA_USER')
        downloader_password = os.environ.get('DOWNLOADER_INSTA_PASS')
        if downloader_username and downloader_password:
            print(f"'{downloader_username}' অ্যাকাউন্ট দিয়ে লগইন করা হচ্ছে...")
            L.login(downloader_username, downloader_password)
    except Exception as e:
        print(f"ত্রুটি: ডাউনলোডার অ্যাকাউন্টে লগইন করার সময় সমস্যা হয়েছে: {e}")
        return

    # লগ ফাইল থেকে পূর্বে প্রসেস করা আইডিগুলো পড়া
    processed_ids = set()
    with open(LOG_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row:
                processed_ids.add(row[0])
    print(f"লগ থেকে {len(processed_ids)} টি আইডি পাওয়া গেছে।")

    # ইন্সটাগ্রাম থেকে পোস্ট এনে লাইকের ভিত্তিতে সাজানো
    print(f"'{TARGET_PROFILE}' থেকে পোস্ট আনা হচ্ছে...")
    profile = instaloader.Profile.from_username(L.context, TARGET_PROFILE)

    posts = [post for i, post in enumerate(profile.get_posts()) if i < POST_COUNT_TO_CHECK]
    sorted_posts = sorted(posts, key=lambda p: p.likes, reverse=True)
    print(f"সেরা {len(sorted_posts)} টি পোস্ট পাওয়া গেছে।")

    for post in sorted_posts:
        if post.is_video and post.shortcode not in processed_ids:
            print(f"\n>> নতুন ভিডিও পাওয়া গেছে: {post.shortcode} (Likes: {post.likes})")

            temp_download_folder = f"temp_{post.shortcode}"
            try:
                L.dirname_pattern = temp_download_folder
                print("ভিডিওটি ডাউনলোড করা হচ্ছে...")
                L.download_post(post, target=post.owner_username)

                video_path = ""
                for f in os.listdir(temp_download_folder):
                    if f.endswith('.mp4'):
                        video_path = os.path.join(temp_download_folder, f)
                        break

                if not video_path:
                    print("ত্রুটি: ডাউনলোড করা ভিডিও ফাইলটি খুঁজে পাওয়া যায়নি।")
                    shutil.rmtree(temp_download_folder)
                    continue

                caption = post.caption if post.caption else "Awesome video!"
                is_uploaded = upload_to_instagram(video_path, caption)

                if is_uploaded:
                    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([post.shortcode, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    print(f"'{post.shortcode}' এর তথ্য লগে লেখা হয়েছে।")

            except Exception as e:
                print(f"ত্রুটি: '{post.shortcode}' আইডি'র ভিডিওটি প্রসেস করার সময় একটি সমস্যা হয়েছে: {e}")
            finally:
                if os.path.exists(temp_download_folder):
                    shutil.rmtree(temp_download_folder)
                    print("অস্থায়ী ডাউনলোড ফোল্ডার পরিষ্কার করা হয়েছে।")

            print(">> পরবর্তী ভিডিও চেক করার জন্য ৬০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
            time.sleep(60)

if __name__ == "__main__":
    main()
    print(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} তারিখের কাজ সম্পন্ন হলো ---")