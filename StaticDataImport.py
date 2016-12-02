"""
Static data imports
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2016 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0
"""

import pandas
#import os
#print os.path.dirname(os.path.abspath(__file__))

# Main folders

#UATPATH = 'O:\\Global Markets\\Credit~2\\Credit~1\\FlowTr~1\\Tools\\FlowTr~1\\'
APPPATH = 'O:\\Global Markets\\Credit~3\\FlowTr~1\\'
MYPATH = APPPATH + 'source\\development\\'
UATPATH = MYPATH
TEMPPATH = APPPATH+'temp\\'
DEFPATH = APPPATH+'definitions\\'
#THPATH = 'O:\\Global Markets\\Credit~2\\Credit~1\\FlowTr~1\\Tools\\TradeH~1\\'
THPATH = APPPATH+'TradeH~1\\'
MAPATH = APPPATH+'ma_logs\\'

# User definitions
gs = pandas.read_csv(DEFPATH+'genericSettings.csv')
logoFile = gs['logoFile'].iloc[0]
LDNFLOWBOOKS = list(gs['LDNFLOWBOOKS'][gs['LDNFLOWBOOKS'].notnull()]) # excludes stlbk atm
TRADERS = list(gs['TRADERS'][gs['TRADERS'].notnull()])
frontToEmail = dict(zip(TRADERS,list(gs['EMAIL'][gs['EMAIL'].notnull()])))
traderLogins = dict(zip(list(gs['WINLOGIN'][gs['WINLOGIN'].notnull()]),TRADERS))

# Chart definitions
xls = pandas.ExcelFile(DEFPATH+'chart_definitions.xls')
#BONDCHARTS = xls.parse('groups')
#BONDCHARTCOLORS = xls.parse('colors')
BONDCHARTS = pandas.read_excel(xls,'groups')
BONDCHARTCOLORS = pandas.read_excel(xls,'colors')

# Bond universe
#bonds = pandas.ExcelFile(DEFPATH+'bonduniverse.xls').parse('list',index_col=0,has_index_names=True)
bonds = pandas.read_excel(DEFPATH+'bonduniverse.xls', sheetname='list',index_col=0)
regsToBondName = {v: k for k, v in dict(bonds['REGS']).items()}
countries = pandas.read_csv(DEFPATH+'countrycodes.csv')
isinsregs = pandas.Series(bonds.index,index=bonds['REGS'])
isins144a = pandas.Series(bonds.index,index=bonds['144A'])
allisins = isinsregs.append(isins144a)
allisins.name = 'Bond'
allisins = allisins.drop(allisins.index.get_duplicates())
SPECIALBONDS = list(gs['SPECIALBONDS'][gs['SPECIALBONDS'].notnull()]) # just 'TNZNIA' atm
bonduniverseexclusionsdf = pandas.read_csv(DEFPATH+'bonduniverseexclusions.csv', header=None)
bonduniverseexclusionsList = list(bonduniverseexclusionsdf[0])
ratingsScale = pandas.read_csv(DEFPATH+'RatingsScale.csv',index_col=0)

# Pricer
bbgToBdmDic = pandas.read_csv(DEFPATH+'bbgToBdmDic.csv',index_col=0)['BondDataModel'].to_dict()
bondRuns = pandas.read_csv(DEFPATH+'runs.csv',index_col=0)
grid_labels = list(pandas.read_csv(DEFPATH+'TabList.csv',header=None)[0])
colFormats = pandas.read_csv(DEFPATH+'colFormats.csv',index_col=0)
runTitleStr = gs['runTitleStr'].iloc[0]

# Trade history
ccy = pandas.read_csv(DEFPATH+'CCY.csv',index_col=0)
counterparties = pandas.read_excel(DEFPATH+'CounterpartyMapping.xlsx',sheetname='Sheet1',index_col=0)

#BloombergHandler
BBGHand = gs['BBGHand'].iloc[0]