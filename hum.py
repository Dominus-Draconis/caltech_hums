"""
Lilia Arrizabalaga
2023-09-25
larrizb@caltech.edu


This place is not a place of honor... 
no highly esteemed deed is commemorated here... 
nothing valued is here.

What is here was dangerous and repulsive to us. 
This message is a warning about danger.
Please why are you reading this.
"""

from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import unicodedata
import csv
import traceback
import time
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.ticker import LinearLocator
import numpy as np
import math

def get_term_classes(term,year):
    """Get list of classes for given year, term.

    Arguments:
        `term` (str): One of FA, WI, or SP (the term to get data for)
        `year` (int): Two digit representation of the year (between 07 and 23)
    Return:
        (dict): Info about the course
    Yes I know I could probably do more of this with bs4 but regex was slightly easier so deal with it.
    """
    class_list = []
    course_infos = []
    url = f'http://schedules.caltech.edu/{term}20{year:02}-{year+1:02}.html'
    try:
        page = urlopen(url)
    except:
        print('Term not found')
        return
    # I tried other decodings and they didn't work
    html = page.read().decode("cp1252") 
    # Split page by department
    depts = re.findall(r"[^#]dept_details[\S\s]*?(?=[^#]dept_details)",html)
    for dept in depts:
        # Get department and only analyze humanities departments
        dept_name = re.findall(r'(?<=dept_details_)(.*?)(?=")', dept)[0]
        depts = ['ENGLISH','HISTORY','HISTORY_AND_PHILOSOPHY_OF_SCIENCE','HUMANITIES','MUSIC','PHILOSOPHY','VISUAL_CULTURE']
        if dept_name not in depts:
            continue
        dept += '<a href="#top' # Add to the end of the department string cuz sometimes it breaks my regex
        # Split department into courses with more bad regex
        courses = re.findall(r'<a href="[^#][\S\s]*?(?=<a href="http:\/\/catalog\.caltech|<a href="#top|<a href="http:\/\/pr\.caltech)',dept)
        for course in courses:
            # Ah see I did use some bs4 :)
            course_soup = BeautifulSoup(course, "html.parser")
            course_name = course_soup.find('a').get_text().strip()
            if not course_name:
                continue
            course_name = unicodedata.normalize("NFKD", course_name)
            course_num = int(re.findall(r'\d+',course_name)[0])
            # Frosh hums are numbered less than 60 and are crosslisted with humanities
            if course_num <= 60 and 'HUMANITIES' in dept:
                req = 'frosh hum'
            # Advanced hums are 90 (98 and 99 are thesis classes)
            elif course_num >= 90 and course_num != 98 and course_num != 99:
                req = 'advanced hum'
            else:
                continue
            # Get the number of sections from the last tage with just two digits (highest section number listed)
            num_sections = re.findall(r'(?<=>)\s*\d{2}(?=\s*<)',course)[-1]
            boldy_bit = None
            max_enrolment = None
            # Extra info (like number of seats) is in a bold tag
            boldy_bit = course_soup.find('b')
            if boldy_bit:
                boldy_bit = boldy_bit.get_text()
                boldy_bit = unicodedata.normalize("NFKD", boldy_bit)
                # Try to find a maximum enrollment (doesnt get all of them smh no consistency)
                max_enrolment = re.findall(r'(?<=enrollment: )\s*\d*(?=\s*students)',boldy_bit, re.IGNORECASE)
                if max_enrolment:
                    max_enrolment = int(max_enrolment[0])
                    # Account for multiple sections with same max enrollment
                    if 'students per section' in boldy_bit:
                        max_enrolment *= int(num_sections)
                # Fake classes! dont count to requierment
                if 'instructor permission required prior to registering' in boldy_bit.lower() or 'class cancelled' in boldy_bit.lower() or 'course cancelled' in boldy_bit.lower():
                    continue
            course_info = {'name': course_name, 'sections': num_sections, 'max enrolment': max_enrolment, 'bold info': boldy_bit, 'req': req, 'year':year,'term':term}
            # If the course was already listed in different department dont double count
            if course_name in class_list:
                continue
            else:
                class_list.append(course_name)
                course_infos.append(course_info)
    return course_infos


def get_years():
    """ Gets all the data and write it to csv file"""
    with open('classes.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['name', 'sections', 'max enrolment', 'bold info', 'req', 'year', 'term'])
        writer.writeheader()
        for year in range(7,24):
            for term in ['FA','WI','SP']:
                print(year, term)
                try:
                    courses = get_term_classes(term,year)
                    if courses:
                        writer.writerows(courses)
                except Exception as err:
                    print(f'http://schedules.caltech.edu/{term}20{year}-{year+1}.html')
                    print(str(err))
                    print('\n')
                    print(traceback.format_exc())
                # Wait a bit cuz sometimes the website is rude
                time.sleep(10)


def anal_seats(req):
    """Get data on total seats per term for the given requierment

    Argument: `req` (str): 'advanced hum' or 'frosh hum'
    Return:
        (dict): dictionary in the from {year: {term: max_enrol, term2: max_enrol,...},...}
    """
    with open('classes_filtered.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        sums = {}
        for row in reader:
            if row['req'] != req:
                continue
            year = f"20{int(row['year']):02}"
            # If the class is not limited enrollemnt dont add anything to the sum
            if not row['max enrolment']:
                max_enrol = 0
            else:
                max_enrol = int(row['max enrolment'])
            if year in sums:
                if row['term'] in sums[year]:
                    sums[year][row['term']] += max_enrol
                else:
                    sums[year][row['term']] = max_enrol
            else:
                sums[year] = {row['term']:max_enrol}
        return sums


def anal_classes(req):
    """Get data on total classes per term for the given requierment

    Argument: `req` (str): 'advanced hum' or 'frosh hum'
    Return:
        (dict): dictionary in the from {year: {term: classes, term2: classes,...},...}
    """
    with open('classes_filtered.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        sums = {}
        for row in reader:
            if row['req'] != req:
                continue
            year = f"20{int(row['year']):02}"
            if year in sums:
                if row['term'] in sums[year]:
                    sums[year][row['term']] += 1
                else:
                    sums[year][row['term']] = 1
            else:
                sums[year] = {row['term']:1}
        return sums


def graph(sums, title, yax):
    """Graph the data as a line chart with the given title and y axis label"""
    years = list(sums.keys())
    # Reorginize data into dict with each term being a list of data sorted by year
    term_data = {
        'FA': [],
        'WI': [],
        'SP': [],
    }
    values = list(sums.values())
    for year in values:
        term_data['FA'].append(year['FA'])
        # 2023 data only has fall term
        try:
            term_data['WI'].append(year['WI'])
            term_data['SP'].append(year['SP'])
        except:
            pass

    fig, ax = plt.subplots(layout='constrained')
    for attribute, measurement in term_data.items():
        line_data = np.arange(len(measurement))  # the label locations
        ax.plot(line_data, measurement, label=attribute)

    # Add some labels and titles
    ax.set_ylabel(yax)
    ax.set_xlabel('Year')
    ax.set_title(title)
    x = np.arange(len(years))
    ax.set_xticks(x, years)
    max_ax = int(plt.yticks()[0][-1])
    ax.set_yticks(range(0,max_ax+1,math.ceil(max_ax/10)))
    ax.legend(loc='upper left')

    plt.show()


def threed(sums):
    """Graph the data as a 3-D surface plot"""
    if sums['2023']:
        del sums['2023']
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    # Make data.
    years = list(sums.keys())
    years = [int(year) for year in years]
    X = np.array(years)
    Y = np.array([0,1,2]) # Represent the terms as an int
    X, Y = np.meshgrid(X, Y)
    Z = np.array([[int(sums[str(year)][term]) for year in years] for term in ['FA','WI','SP']]) # Get height

    # Plot the surface.
    surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm,
                        linewidth=0, antialiased=False)

    # Add a color bar which maps values to colors.
    fig.colorbar(surf, shrink=0.5, aspect=5)

    plt.show()


if __name__ == '__main__':
    #get_years()
    graph(anal_seats('advanced hum'),'Number of Seats in Limited Enrollment Advanced Humanities', '# seats')
    graph(anal_seats('frosh hum'), 'Number of Seats in Limited Enrollment Frosh Humanities', '# seats')
    graph(anal_classes('advanced hum'),'Number of Advanced Humanities', '# classes')
    graph(anal_classes('frosh hum'), 'Number of Frosh Humanities', '# classes')
    threed(anal_seats('advanced hum'))
