import scrapy
from scrapy_webdriver.http import WebdriverRequest
import json
from urlparse import urljoin
import time
import hashlib
from selenium.common.exceptions import StaleElementReferenceException

class Row(scrapy.Item):
    Company = scrapy.Field()
    Website = scrapy.Field()
    Symbol = scrapy.Field()
    Industry = scrapy.Field()
    Contact = scrapy.Field()
    Date = scrapy.Field()
    FinancialYear = scrapy.Field()
    No = scrapy.Field()
    FinancialQuarter = scrapy.Field()
    Revenue = scrapy.Field()
    ProfitBeforeTax = scrapy.Field()
    NetProfit = scrapy.Field()
    EarningPerShare = scrapy.Field()
    Dividend = scrapy.Field()
    NTA = scrapy.Field()
    Download = scrapy.Field()


class BlogSpider(scrapy.Spider):
    name = 'MalaysiaStock.biz'

    @property
    def start_urls(self):
        base = 'http://www.malaysiastock.biz/Listed-Companies.aspx?type=A'
        values = ['0'] + [chr(x) for x in range(65,91)]
        return ['%s&value=%s' % (base, v) for v in values]

    def parse(self, response):
        for url in response.css('#MainContent_tStock h3 a::attr("href")'):
            url = url.extract()
            yield WebdriverRequest(urljoin(response.url, url), callback=self.parse_company)

    def _get_pagers(self, d):
        return d.find_elements_by_css_selector('.pgr tbody > tr > td > a')

    def _css(self, el, sel):
        return el.find_elements_by_css_selector(sel)

    def _get_pager_element(self, d, href):
        for i in self._get_pagers(d):
            if i.get_attribute("href") == href:
                return i

    def parse_company(self, response):
        driver = response.webdriver

        pagers = [i.get_attribute('href') for i in self._get_pagers(driver)]

        for j in self.extract_json(driver):
            yield j

        compare = pagers
        for page_url in pagers:
            link = self._get_pager_element(driver, page_url)
            link.click()
            compare = self.wait_for_change(compare, driver,
                lambda x: [i.get_attribute("href") for i in self._get_pagers(x)]
            )
        
            for j in self.extract_json(driver):
                yield j

    def wait_for_change(self, compare, driver, func):
        while True:
            c = None
            while c is None:
                try:
                    c = func(driver)
                except StaleElementReferenceException, e:
                    c = None
                    time.sleep(5)

            hash1 = hashlib.md5('|'.join(c)).hexdigest()
            hash2 = hashlib.md5('|'.join(compare)).hexdigest()
            if hash1 != hash2:
                return c
            print "Waiting for Page Update (%s, %s)" % (hash1, hash2)
            time.sleep(5)

    def extract_json(self, driver):
        data_els = driver.find_elements_by_css_selector(
            "#MainContent_gvReport > tbody > tr"
        )

        if not driver.find_elements_by_css_selector(
            '#MainContent_lbCorporateName'
            ):
            return 

        company = driver.find_elements_by_css_selector(
            '#MainContent_lbCorporateName'
            )[0].text.replace(": ","").strip()

        website = driver.find_elements_by_css_selector(
            '#MainContent_lbWebsite'
        )[0].text.replace(": ","").strip()

        symbol = driver.find_elements_by_css_selector(
            '#MainContent_lbSymbolCode'
        )[0].text.replace(": ","").strip()

        industry = driver.find_elements_by_css_selector(
            '#MainContent_lbIndustry'
        )[0].text.replace(": ","").strip()

        contact = driver.find_elements_by_css_selector(
            '#MainContent_lbContact'
        )[0].text.replace(": ","").strip()



        headers = [
            'Date',
            'FinancialYear',
            'No',
            'FinancialQuarter',
            'Revenue',
            'ProfitBeforeTax',
            'NetProfit',
            'EarningPerShare',
            'Dividend',
            'NTA',
            'Download'
        ]

        schema = {
            'Date': lambda x:x,
            'FinancialYear': lambda x:x,
            'No': lambda x: int(x),
            'FinancialQuarter': lambda x:x,
            'Revenue': lambda x: int(x.replace(',','')) * 1000,
            'ProfitBeforeTax': lambda x: int(x.replace(',','')) * 1000,
            'NetProfit': lambda x:int(x.replace(',','')) * 1000,
            'EarningPerShare': lambda x: float(x),
            'Dividend': lambda x: float(x),
            'NTA': lambda x: float(x),
            'Download': lambda x: None
        }

        for tr in data_els:
            out = {
                'Company': company,
                'Website': website,
                'Symbol': symbol,
                'Industry': industry,
                'Contact': contact
            }
            if tr.get_attribute("class") == "pgr":
                continue

            for idx, td in enumerate(self._css(tr, "td")):
                k = headers[idx]
                v = schema[k](td.text.strip())
                out[k] = v
            if out:
                yield Row(out)


