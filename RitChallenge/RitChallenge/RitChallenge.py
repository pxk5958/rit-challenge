import csv
import sys
import sqlite3
import re
import os
from datetime import date as Date
from enum import Enum

class TransactionType(Enum):
    Cab = 1
    Restaurants = 2
    Shopping = 3   
    Entertainment = 4
    Rent = 5
    Utilities = 6
    Fuel = 7
    Penalties = 8
    ATM = 9
    Other = 10

    def getType(description):
        description = description.lower()
        descriptionWords = re.split(' |:|\*', description)
        if any(item in description for item in ['late']):
            return TransactionType.Penalties
        elif any(item in descriptionWords for item in ['firstservice', 'resident']):
            return TransactionType.Rent
        elif any(item in descriptionWords for item in ['atm']):
            return TransactionType.ATM
        elif any(item in description for item in ['target', 'walmart', 'amazon', 'nordstrom', 'paypal', '3 sisters']):
            return TransactionType.Shopping
        elif any(item in descriptionWords for item in ['uber']):
            return TransactionType.Cab
        elif any(item in descriptionWords for item in ['netflix']):
            return TransactionType.Entertainment
        elif any(item in descriptionWords for item in ['chevron', 'exxon', 'shell']):
            return TransactionType.Fuel
        elif any(item in description for item in ['mobile gas']):
            return TransactionType.Utilities
        elif any(item in description for item in 
                 ['mesh on mass', 'brugge brasserie', 'mama carolla\'s old italian', 'recess', 'yats', 'twenty tap',
                  'goose the market', 'siam square', 'shapiro\'s delicatessen', 'bluebeard', 'iaria\'s italian restaurant',
                  'bazbeaux', 'union 50', 'taste cafe & marketplace', 'st. elmo steak house', 'cafe patachou', 
                  'the tamale place', 'mug n\' bun', 'the loft at trader\'s point creamery', 'shoefly public house', 
                  'scotty\'s brewhouse', 'sahm\'s place', 'delicia', 'pizzology'
                  ]):
            return TransactionType.Restaurants
        else:
            return TransactionType.Other

    def getPriority(type):
        if type is [TransactionType.Penalties]:
            return 1
        elif type in [TransactionType.Restaurants, TransactionType.Entertainment, TransactionType.Cab]:
            return 2
        elif type in [TransactionType.Shopping]:
            return 3
        elif type in [TransactionType.ATM, TransactionType.Other]:
            return 4
        elif type in [TransactionType.Rent, TransactionType.Utilities, TransactionType.Fuel]:
            return 5

def main():
    while(True):
        filepath = str(input('Enter the transactions file path relative to current directory: '))       
        if os.path.isfile(filepath) is True:
            break
        else:
            print('File does not exist! Please try again.')

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    
    # Create table
    c.execute('''CREATE TABLE expenses
                 (date text, description text, amount real, type integer, priority integer)''')

    with open(filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile, ['date', 'description', 'amount'])
        for row in reader:
            #print(row['date'], row['description'], row['amount'])
            type = TransactionType.getType(row['description'].strip())
            c.execute('INSERT INTO expenses VALUES (?,?,?,?,?)',
                      (row['date'].strip(),
                       row['description'].strip(),
                       float(row['amount'].strip()),
                       type.value,
                       TransactionType.getPriority(type)))

    # Save (commit) the changes
    conn.commit()

    c.execute('''SELECT min(datetime(date)), max(datetime(date)) FROM expenses''')
    rows = c.fetchall()
    startDate = rows[0][0]
    endDate = rows[0][1]
    #print('Start : ' + startDate)
    #print('End : ' + endDate)

    c.execute('''SELECT julianday(?) - julianday(?) FROM expenses''', (endDate, startDate))
    rows = c.fetchall()
    approxNumMonths = rows[0][0]/30
    #print('ApproxNumMonths : ' + str(approxNumMonths))
    
    print('\n\nHere\'s a breakdown of your expenses:')

    print('\n{:<30} {:<30} {:<30} {:<30}'.format('CATEGORY', 'NUMBER OF TRANSACTIONS', 'TOTAL EXPENDITURE', 'MONTHLY (APPROX.)'))
    underline = '========================='
    print('{:<30} {:<30} {:<30} {:<30}'.format(underline, underline, underline, underline))

    tips = '\n\nTips:'
    luxuriesStatementAdded = False

    for row in c.execute('''select type, COUNT(*), SUM(amount) as Expenditure, SUM(amount)/?
       from expenses group by type ORDER BY priority ASC, Expenditure DESC''', (approxNumMonths,)):
        type = TransactionType(row[0])
        numberOfTransactions = row[1]
        expenditure = round(row[2], 2)
        monthly = round(row[3], 2)
        print('{:<30} {:<30} {:<30} {:<30}'.format(type.name, 
                                                   numberOfTransactions, 
                                                   '$' + '{:.2f}'.format(expenditure), 
                                                   '$' + '{:.2f}'.format(monthly)))

        if type is TransactionType.Penalties and expenditure > 0:
            tips += '\n\n* Avoid paying penalties due to late payment of rent, etc. Over the last ' + str(round(approxNumMonths)) \
                    + ' months, you have paid $' + str(expenditure) + ' for such penalties unnecessarily!'
        elif type in [TransactionType.Restaurants, TransactionType.Cab, TransactionType.Entertainment] and expenditure > 0:
            if luxuriesStatementAdded is False:
                tips += '\n\nThese are luxuries for which you can spend less in order to save more for your goal, since they aren\'t really necessities:'
                luxuriesStatementAdded = True
            if type is TransactionType.Restaurants:
                tips += '\n\n* Did you know you could save a lot more cooking by yourself rather than eating out? Over the last ' + str(round(approxNumMonths)) \
                        + ' months, you have spent $' + str(expenditure) + ' (approximately $' + str(monthly) + ' per month) on eating out ' + str(numberOfTransactions) + ' times!'
            elif type is TransactionType.Cab:
                tips += '\n\n* Rather than using taxicabs, plan out your travel in advance and use public transport to save money.  Over the last ' + str(round(approxNumMonths)) \
                        + ' months, you have spent $' + str(expenditure) + ' (approximately $' + str(monthly) + ' per month) on taxicabs ' + str(numberOfTransactions) + ' times!'
            elif type is TransactionType.Entertainment:
                tips += '\n\n* We know that "All work and no play makes Jack a dull boy!" but if you really want to save more, you could do so many things for free to keep' \
                        + ' yourself entertained. Go out and play some sports! It would keep you fit too. Over the last ' + str(round(approxNumMonths)) \
                        + ' months, you have spent $' + str(expenditure) + ' on entertainment.'
        elif type is TransactionType.Shopping and expenditure > 0:
            tips += '\n\nComing to shopping:'
            tips += '\n\n* You could try to reduce some shopping or find cheaper alternatives if you could. Over the last ' + str(round(approxNumMonths)) \
                    + ' months, you have spent $' + str(expenditure) + ' (approximately $' + str(monthly) + ' per month) on shopping.'
    
    print(tips)

    conn.close()
    
if __name__ == "__main__":
    #sys.exit(int(main() or 0))
    main()