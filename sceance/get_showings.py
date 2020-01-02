# -*- coding: utf-8 -*-
'''
Starts a Firfox headless brower to see if movies on your watchlist are playing
at any of your favorite theaters.

Favorite theaters are taken from a txt file (extracted from "theaters.txt").
These showtimes are compared to a watchlist (extracted from "watchlist.txt")

-samuel mignot-
'''

# ------------------- #
# imports             #
# ------------------- #

# external
import os
import datetime
import re
import collections
import pickle

from distutils.util import strtobool
from contextlib import contextmanager

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


# internal
import file_helpers

# ------------------- #
# constants           #
# ------------------- #

GOOGLE_CSS_SELECTORS = {
    "see_more": "div[class^='hide-focus-ring']",
    "address": "span.LrzXr",
    "show_days": "li.tb_l",
    "showings": "div.lr_c_fcb.lr-s-stor",
    "film_details": "div.wwUB2c.PZPZlf",
    "english_lang": "div.std.stp.card-section"
}

FILM_DETAIL_SEP = '‧'
DATA_PATH = 'data/'

# ------------------- #
# named_tuples        #
# ------------------- #

Theater = collections.namedtuple('Theater', ['name', 'address'])
Film = collections.namedtuple('Film', ['name', 'release', 'genre', 'length'])

# ----------------------- #
# selenium driver helpers #
# ----------------------- #

def get_element_or_default(driver, element_selector, default, element_name):
    '''gets an element from the current page with the selector, or returns a default and prints an error message'''
    try:
        element = driver.find_element_by_css_selector(element_selector)
        return element
    except selenium.common.exceptions.NoSuchElementException:
        print(f"could not find {element_name} on {driver.current_url} with selector {element_selector}.")
        if not default:
            print(f"there is no default {element_name} skipped")
            return -1
        print(f"{element_name} set to default value of {default}.")
        return default

def get_elements_or_default(driver, element_selector, default, element_name):
    '''gets multiple elements from the current page with the selector, or returns a default and prints an error message'''
    try:
        elements = driver.find_elements_by_css_selector(element_selector)
        return element
    except selenium.common.exceptions.NoSuchElementException:
        print(f"could not find {element_name} on {driver.current_url} with selector {element_selector}.")
        if not default:
            print(f"there is no default {element_name} skipped")
            return -1
        print(f"{element_name} set to default value of {default}.")
        return default

def start_brower(headless=True):
    '''starts and returns a selenium firefox brower. Takes a paremeter to determine headedness'''
    options = Options()
    options.headless = headless
    profile = webdriver.FirefoxProfile()
    profile.set_preference('intl.accept_languages', 'en_GB')

    driver = webdriver.Firefox(
        executable_path=GeckoDriverManager().install(),
        firefox_profile=profile,
        options=options,
        service_log_path=os.path.devnull
    )
    return driver

@contextmanager
def wait_for_new_window(driver, timeout=10):
    '''makes sure a new window has loaded before progressing'''
    handles_before = driver.window_handles
    yield
    WebDriverWait(driver, timeout).until(
        lambda driver: len(handles_before) != len(driver.window_handles))

# ----------------------- #
# extraction helpers      #
# ----------------------- #

def get_movie_lengths(film_links):
    '''Takes a dictionary of film links and gets movie lengths if they haven't already been saved.'''
    film_length_dict = {}
    if os.path.exists(f'{DATA_PATH}film_length.pickle'):
        with open(f'{DATA_PATH}film_length.pickle', 'rb') as flf:
            film_length_dict = pickle.load(flf)

    new_films = {k: v for k, v in film_links.items() if k not in film_length_dict.keys()}

    if not new_films:
        return film_length_dict

    driver = start_brower(True)
    for k, url in new_films.items():
        driver.get(url)
        film_details = get_element_or_default(
            driver,
            GOOGLE_CSS_SELECTORS['film_details'],
            FILM_DETAIL_SEP.join(["not specified", "not specified", "1h 50m"]),
            "film details"
        )
        if type(film_details) is not str:
            film_details = film_details.text
        release_date, film_genre, film_length = film_details.split(FILM_DETAIL_SEP)
        cur_film = Film(
            name=k.strip(),
            release=release_date.strip(),
            genre=film_genre.strip(),
            length=tuple(map(int, film_length[:-1].strip().split('h ')))
        )
        print(cur_film)
        film_length_dict[k] = cur_film

    with open(f'{DATA_PATH}film_length.pickle', 'wb') as flf:
        pickle.dump(film_length_dict, flf)

    return film_length_dict

def get_dates(datelist):
    '''Takes a string of concatenated standard dates and return a list of military time tuples.'''
    date_pattern = r"\d{1,2}\:\d{2}(?:am|pm)"
    matches = re.findall(date_pattern, datelist)
    tupled_matches = [list(map(int, match[:-2].split(":")))+[match[-2:]] for match in matches]
    military_time_tuples = [tuple([match[0]+12, match[1]]) if match[2] == 'pm' and match[0] != 12
                            else tuple(match[:2]) for match in tupled_matches]
    return military_time_tuples

def get_possible_showtimes(movie_showtimes, film_length_dict, watchlist):
    '''returns a Film object to datetime array dict with playtimes for all movies found in watchlist'''
    possible_showtimes = {}
    for movie_name, showtimes in movie_showtimes.items():
        if movie_name.lower() in watchlist:
            for showtime in showtimes:
                possible_showtimes.setdefault(film_length_dict[movie_name], []).append(showtime)
    return possible_showtimes

# ---------------------- #
# main function          #
# ---------------------- #

def get_watchlist_showings(headless):
    '''Do X and return a list.'''
    theater_search_placeholder = "https://www.google.com/search?q={theater_name}+showtimes&lr=lang_en"

    movie_showtimes = {}
    film_links = {}

    driver = start_brower(headless)

    watchlist = file_helpers.get_watchlist()
    theaters = file_helpers.get_theaters()

    for theater in theaters:
        url = theater_search_placeholder.format(theater_name=(theater[:-1].replace(" ", "+")))
        driver.get(url)
        address = driver.find_element_by_css_selector(GOOGLE_CSS_SELECTORS['address']).text
        movie_theater = Theater(name=theater[:-1], address=address)
        print(f"{movie_theater}\n")
        show_days = driver.find_elements_by_css_selector(GOOGLE_CSS_SELECTORS['show_days'])
        date_s = datetime.datetime.today()
        for day in show_days:
            day.click()
            see_more_button = get_element_or_default(
                driver,
                GOOGLE_CSS_SELECTORS['see_more'],
                "none",
                "see more button"
            )
            if type(see_more_button) is not str:
                if not strtobool(see_more_button.get_attribute('aria-expanded')):
                    driver.execute_script("arguments[0].click();", see_more_button)
            showings = driver.find_elements_by_css_selector(GOOGLE_CSS_SELECTORS['showings'])
            for showing in showings:
                if not len(showing.text.splitlines()) == 3:
                    continue

                name, datelist = showing.text.splitlines()[1:]
                link = showing.find_element_by_css_selector('a')
                film_links[name] = link.get_attribute('href')

                show_times = get_dates(datelist)
                for show_time in show_times:
                    possible_showtime = date_s.replace(hour=show_time[0], minute=show_time[1])
                    movie_showtimes.setdefault(name, []).append((movie_theater, possible_showtime))
            date_s += datetime.timedelta(days=1)
    driver.quit()
    print(movie_showtimes.keys())
    film_links = {k: v for k, v in film_links.items() if k.lower() in watchlist}
    film_length_dict = get_movie_lengths(film_links)
    possible_showtimes = get_possible_showtimes(movie_showtimes, film_length_dict, watchlist)
    return possible_showtimes

if __name__ == "__main__":
    get_watchlist_showings(headless=True)