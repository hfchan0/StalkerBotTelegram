# Reference: https://proxyway.com/guides/how-to-scrape-instagram#HowtoScrapeInstagramLegally
# Reference: https://medium.com/marketingdatascience/%E8%B7%9F%E8%91%97ig%E6%BD%AE%E6%B5%81%E4%BE%86%E7%88%AC%E8%9F%B2-%E7%94%A8selenium%E5%B8%B6%E6%82%A8%E8%87%AA%E5%8B%95%E7%99%BB%E5%85%A5-ig-%E7%B3%BB%E5%88%971-%E9%99%84python%E7%A8%8B%E5%BC%8F%E7%A2%BC-846d57f73cac
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import time

from pprint import pprint
import json
from selenium_stealth import stealth
from bs4 import BeautifulSoup
usernames = ["minn.__.ju", "_yujin_an", "akaonikou"]
base_address = 'https://instagram.com'
output = {}
browser = None

def prepare_browser():
    browser_options = webdriver.ChromeOptions()
    #proxy = "server:port"
    #browser_options.add_argument(f'--proxy-server={proxy}')
    browser_options.add_argument("start-maximized")
    browser_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    browser_options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options = browser_options, executable_path='./chromedriver_win32/chromedriver')
    stealth(driver,
        user_agent= 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36',
        languages= ["en-US", "en"],
        vendor=  "Google Inc.",
        platform=  "Win32",
        webgl_vendor=  "Intel Inc.",
        renderer=  "Intel Iris OpenGL Engine",
        fix_hairline= False,
        run_on_insecure_origins= False,
        )
    return driver

def parse_data(username, user_data):
    captions = []
    if len(user_data['edge_owner_to_timeline_media']['edges']) > 0:
        for node in user_data['edge_owner_to_timeline_media']['edges']:
            if len(node['node']['edge_media_to_caption']['edges']) > 0:
                if node['node']['edge_media_to_caption']['edges'][0]['node']['text']:
                    captions.append(
                        node['node']['edge_media_to_caption']['edges'][0]['node']['text']
                    )
                
    output[username] = {
        'name': user_data['full_name'],
        'category': user_data['category_name'],
        'followers': user_data['edge_followed_by']['count'],
        'posts': captions,
    }

def scrape(username):
    # url = f'https://instagram.com/{username}/?__a=1&__d=dis'
    # url = f'https://instagram.com/{username}/?__a=1'
    url = base_address + f'/{username}'
    browser.get(url)
    print (f"Attempting: {browser.current_url}")
    if "login" in browser.current_url:
        print ("Failed/ redir to login")
        browser.quit()
    else:
        print ("Success")
        resp_body = browser.find_element(By.TAG_NAME, "body").text
        data_json = json.loads(resp_body)
        print(data_json)
        user_data = data_json['graphql']['user']
        parse_data(username, user_data)
        browser.quit()

def login_ig():
    # ------ 前往該網址 ------
    base_address = "https://www.google.com/?hl=en"
    browser.get(base_address) 

    # # ------ 填入帳號與密碼 ------
    # WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, 'username')))

    # # ------ 網頁元素定位 ------
    # username_input = browser.find_element("name", 'username')
    # password_input = browser.find_element("name", 'password')
    # print("inputing username and password...")

    # # ------ 輸入帳號密碼 ------
    # username_input.send_keys("skrz0201")
    # password_input.send_keys("mess41220")

    # # ------ 登入 ------
    # WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH,
    # '//*[@id="loginForm"]/div/div[3]/button/div')))
    # # ------ 網頁元素定位 ------
    # login_click = browser.find_element('xpath', '//*[@id="loginForm"]/div/div[3]/button/div')
    # # ------ 點擊登入鍵 ------
    # login_click.click()
    # time.sleep(3000)
    # browser.get(base_address)

    popup_handler = browser.find_element(By.PARTIAL_LINK_TEXT, 'Feeling')!!
    print(popup_handler)
    popup_handler.click()

def driver():
    global browser
    browser = prepare_browser()
    login_ig()
    # for username in usernames:
    #     scrape(username)

if __name__ == '__main__':
    driver()
    pprint(output)