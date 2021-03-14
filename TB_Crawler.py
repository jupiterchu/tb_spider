import csv
import json
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys

USER_DIR = "user"
WEBDRIVER_PATH = "chromedriver.exe"


class TaoBaoCrawler:
    def __init__(self, keywords):
        self.keywords = keywords
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument("disable-blink-features=AutomationControlled")
        # chrome_option.add_argument("--user-data-dir={}".format(USER_DIR))

        self.browser = webdriver.Chrome(executable_path=WEBDRIVER_PATH)
        with open("stealth.min.js", 'r', encoding="utf-8") as f:
            js_code = f.read()

        self.browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": js_code,
        })

        with open('taobao.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'tag', 'release_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    def search_keyword(self, keyword):
        """查询目录"""
        input_table = self.browser.find_element_by_css_selector(".search-combobox-input")
        input_table.send_keys(keyword)
        search_button = self.browser.find_element_by_css_selector("button[class='btn-search tb-bg']")
        search_button.click()

    def search_sort_element(self):
        """按价格排序"""
        sort = self.browser.find_element_by_css_selector("a[data-value='sale-desc']")
        sort.click()

    def parse(self, html):
        """解析数据"""
        soup = BeautifulSoup(html, 'lxml')
        item_array = soup.select(".items > div[data-category='auctions']")
        for item in item_array:
            result = {
                'price': item.select_one('strong').text,
                'deal_num': item.select_one('.deal-cnt').text,
                'title': item.select_one('img')['alt'],
            }

            self.pipeline(result)


    def pipeline(self, data):
        """存储数据到 csv"""
        with open('taobao.csv', 'a+', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'price', 'deal_num']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(data)

    def click_next_page(self):
        next_page = self.browser.find_element_by_css_selector("li[class='item next']")
        next_page.click()

    def pass_slide(self):
        # 定位验证码所在iframe环境
        iframe = self.browser.find_element_by_css_selector("iframe[src*='punish']")
        # 切换至该iframe环境
        self.browser.switch_to.frame(iframe)
        slide = self.browser.find_element_by_css_selector("#nc_1_n1z")
        ActionChains(self.browser).click_and_hold(slide).move_by_offset(300, 0).perform()
        # 切回主环境
        self.browser.switch_to.window(self.browser.window_handles[0])
        # 重新点击下一页

    def check_slide(self):
        try:
            iframe = self.browser.find_element_by_css_selector('iframe[src*="punish"]')
            return True
        except NoSuchElementException:
            return False

    def login(self):

        url = 'https://login.taobao.com/member/login.jhtml?spm=a21bo.2017.754894437.1.5af911d98wueqf&f=top&redirectURL=https%3A%2F%2Fwww.taobao.com%2F'
        self.browser.get(url)
        account = self.browser.find_element_by_css_selector('#fm-login-id')
        password = self.browser.find_element_by_css_selector('#fm-login-password')
        account.send_keys('account')
        password.send_keys('password')
        button = self.browser.find_element_by_css_selector('.fm-button')
        button.click()
        try:
            slide = self.browser.find_element_by_css_selector("#nc_1_n1z")
            ActionChains(self.browser).click_and_hold(slide).move_by_offset(300, 0).perform()
        except NoSuchElementException:
            pass

    def store_cookie(self):
        cookies = self.browser.get_cookies()
        json_cookies = json.dumps(cookies)
        with open('tb_cookies.json', 'w') as f:
            f.write(json_cookies)

    def load_cookie(self):
        if os.path.exists('tb_cookies.json'):
            with open('tb_cookies.json', 'r') as f:
                json_cookies = json.loads(f.read())
            cookie = {'name': json_cookies[0]['name'], 'value': json_cookies[0]['value']}
            self.browser.add_cookie(cookie)
        else:
            self.login()
            self.store_cookie()

    def run(self):

        self.load_cookie()
        time.sleep(2)
        for keyword in self.keywords:
            index_url = 'https://taobao.com'
            self.browser.get(index_url)
            self.search_keyword(keyword)
            time.sleep(2)
            self.search_sort_element()
            ActionChains(self.browser).send_keys(Keys.END).perform()
            ActionChains(self.browser).send_keys(Keys.HOME).perform()

            for page_num in range(1, 3):
                if page_num == 1:
                    self.parse(self.browser.page_source)
                self.click_next_page()


if __name__ == '__main__':
    taobao = TaoBaoCrawler(['键盘', ])
    taobao.run()
