from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import urllib
import datetime
import re
import collections
import requests

Theater = collections.namedtuple('Theater', ['name', 'address'])
movie_showtimes = {}
theater_search = "https://www.google.com/search?q={theater_name}+showtimes"

def get_dates(datelist):
    date_pattern = r"(\d{2}\:\d{2})"
    matches = re.findall(date_pattern, datelist)
    tupled_matches = [tuple(map(int, match.split(":"))) for match in matches]
    print(tupled_matches)
    return tupled_matches

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_experimental_option('prefs', {'intl.accept_languages': 'en_US'})

driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

with open("theaters.txt") as f:
    theaters = f.readlines()

for theater in theaters:
    url = theater_search.format(theater_name=urllib.parse.quote_plus(theater))
    print(url)
    driver.get(url)
    address = driver.find_element_by_css_selector("span.LrzXr").text
    movie_theater = Theater(name=theater[:-1], address=address)
    print(movie_theater)
    print("")
    show_days = driver.find_elements_by_css_selector("li.tb_l")
    date_s = datetime.datetime.today()
    for i, day in enumerate(show_days):
        date_s += datetime.timedelta(days=1)
        print(date_s)
        day.click()
        showings = driver.find_elements_by_css_selector("div.lr_c_fcb.lr-s-stor")
        for showing in showings:
            if(len(showing.text.splitlines())<3): continue
            name, datelist = showing.text.splitlines()[1:]
            print(name)
            print(datelist)
            show_times = get_dates(datelist)
            for show_time in show_times:
                if name in movie_showtimes.keys():
                    movie_showtimes[name].append((movie_theater, date_s.replace(hour=show_time[0], minute=show_time[1])))
                else:
                    movie_showtimes[name] = [(movie_theater, date_s.replace(hour=show_time[0], minute=show_time[1]))]
print(movie_showtimes)

driver.quit()
