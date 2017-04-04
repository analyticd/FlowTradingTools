"""
Tree display of Front risk
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Class:
RiskTreeManager
"""

import wx
import pandas
import datetime
import threading
import time
import pythoncom
import os
from wx.lib.pubsub import pub

import blpapiwrapper
from StaticDataImport import ccy, countries, bonds, BBGHand, TEMPPATH, isinsregs, SPECIALBONDS, allisins

todayDateSTR = datetime.datetime.today().strftime('%d/%m/%y')
_offsets = (3, 1, 1, 1, 1, 1, 2)
yesterdayDateSTR = (datetime.datetime.today() - datetime.timedelta(days=_offsets[datetime.datetime.today().weekday()])).strftime('%Y-%m-%d')



def tradeVolume(th,key,item):
    return th.df[(th.df[key]==item) & (th.df['Date']==todayDateSTR)]['Qty'].sum()

class MessageContainer():
    def __init__(self, data):
        self.data = data


class BondPriceUpdateMessage():
    def __init__(self, bond, booklist, price):
        self.bond = bond
        self.booklist = booklist
        self.price = price


#----------------------------------------------------------------------

class RiskTreeManager():
    """Class to define the Risk Tree Panel
    It will manage two DataFrames, one that has position per bond, and one that has position and P&L per ISIN.

    Attributes:

    Methods:
    __init__()

    """
    def __init__(self, th, parent):
        """
        Keyword arguments:
        parent : parent 
        th = trade history (defaults to empty array if not specified)
        """
        self.th = th
        self.parent = parent
        self.EODPricesFilled = False
        #self.LivePricesFilled = False
        self.bdmReady = False
        self.lock = threading.Lock()
        self.cntrymap = countries.set_index('Country code')
        self.cntrymap.rename(columns={'Long name':'LongCountry'}, inplace=True)
        self.riskFreeIssuers = ['T', 'DBR', 'UKT', 'OBL']
        #RISK TREE
        self.th.positions['EODPrice'] = 0.0
        self.th.positions['EODValue'] = 0.0
        #self.th.positions['Risk'] = 0.0
        self.displayPositions = self.th.positions[(self.th.positions['Qty']<=-1) | (self.th.positions['Qty']>=1)].copy()
        # del self.displayPositions['REGS']
        # del self.displayPositions['144A']
        # self.displayPositions = self.displayPositions.join(bonds['REGS'])
        self.displayPositions = self.displayPositions.join(self.cntrymap['LongCountry'], on='Country')
        self.displayPositions['NewTrades'] = 0.0
        self.displayGroup = self.displayPositions.groupby(['Region','LongCountry','Issuer','Bond']).sum()
        #self.rateDisplayGroup = self.displayPositions.groupby(['CCY','Bond']).sum()
        #print self.rateDisplayGroup
        #BOOK AND PnL TREE
        self.th.positionsByISINBook['Qty'] = self.th.positionsByISINBook['SOD_Pos']#Qty will be current, SOD is start of day
        for c in ['EODPrice','EODValue','PriceY','Risk','USDQty','PriceT','SODPnL','TradePnL','TotalPnL','MK','PRINCIPAL_FACTOR','RISK_MID', 'SAVG', 'IRRisk']:
            self.th.positionsByISINBook[c] = pandas.np.nan
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.cntrymap['LongCountry'],on='Country')
        self.th.positionsByISINBook.set_index('Key',inplace=True)
        self.th.positionsByISINBook['NewTrades'] = 0.0
        self.displayGroupBook = self.th.positionsByISINBook.groupby(['Book','LongCountry','Issuer','Bond','Series']).sum()
        self.traded_bonds = [] # IMPORTANT
        self.new_trades = self.th.df[self.th.df['Date']==todayDateSTR].copy()
        self.EODPrices = self.th.positions['EODPrice'].copy()
        pub.subscribe(self.updatePrice, "BOND_PRICE_UPDATE")
        pub.subscribe(self.switchBDMReady, "BDM_READY")
        pub.subscribe(self.onUpdateTree, "POSITION_UPDATE")
        pass

    def switchBDMReady(self, message):
        self.bdm = message.data
        self.bdmReady = True
        self.treeRebuild()
        pass

    def updatePrice(self, message):
        if self.bdmReady:
            self.lock.acquire()
            bond = message.data.name
            idx = (self.th.positionsByISINBook['Bond'] == bond)
            if idx.sum() > 0:
                price = message.data['MID']
                self.th.positionsByISINBook.loc[idx,'PriceT'] = price
                self.th.positionsByISINBook.loc[idx,'SODPnL'] = self.th.positionsByISINBook.loc[idx,'SOD_Pos'] * self.bdm.df.loc[bond,'PRINCIPAL_FACTOR'] * (price - self.th.positionsByISINBook.loc[idx,'PriceY'])/100.
                # self.th.positionsByISINBook.loc[idx,'SODPnL'].fillna(0, inplace=True) # this is a view
                self.th.positionsByISINBook.loc[idx,'SODPnL'] = self.th.positionsByISINBook.loc[idx,'SODPnL'].fillna(0) # this is a view
                fx = ccy.at[bonds.at[bond,'CRNCY'], '2017']
                if bond in self.new_trades['Bond'].values:
                    for (k, grp) in self.positionDeltas:
                        isin = k[1]
                        try:
                            if allisins[isin] == bond:#grp['Qty'].sum()!=0 
                                idx = (self.new_trades['ISIN'] == isin) & (self.new_trades['Book'] == k[0])
                                self.new_trades.loc[idx,'TradePnL'] = self.new_trades.loc[idx,'Qty']*(price-self.new_trades.loc[idx,'Price'])/100.
                                self.th.positionsByISINBook.at[k[0]+'-'+k[1],'TradePnL'] = self.th.positionsByISINBook.at[k[0]+'-'+k[1],'PRINCIPAL_FACTOR'] * self.new_trades.loc[idx,'TradePnL'].sum()
                        except:
                            #bond is dummy
                            pass
                ########
                bondlines = (self.th.positionsByISINBook['Bond'] == bond)
                self.th.positionsByISINBook.loc[bondlines,'TotalPnL'] = self.th.positionsByISINBook.loc[bondlines,'SODPnL']/fx + self.th.positionsByISINBook.loc[bondlines,'TradePnL']/fx
                booklist = list(self.th.positionsByISINBook.loc[bondlines,'Book'].drop_duplicates())
                message = BondPriceUpdateMessage(bond=bond, booklist=booklist, price=price)
                pub.sendMessage('RISKTREE_BOND_PRICE_UPDATE', message=message)
            self.lock.release()
        pass

    def onFillEODPrices(self, fc):
        """Function to download EOD Prices from Front and calculate PV.
        fc : front connection FO_Toolkit > FrontConnection class instance
        """
        savepath = TEMPPATH + 'EODPrices.csv'
        noEODPricesFile = not(os.path.exists(savepath)) or datetime.datetime.fromtimestamp(os.path.getmtime(savepath)).date()<datetime.datetime.today().date()
        if noEODPricesFile:
            for idx, row in self.th.positionsByISINBook.iterrows():
                self.th.positionsByISINBook.loc[idx, 'PriceY'] = fc.historical_price_query(row['ISIN'], yesterdayDateSTR)
            self.th.positionsByISINBook.to_csv(TEMPPATH+'SOD_risk_prices.csv')
            for bond in self.displayPositions.index:
                self.th.positions.loc[bond,'EODPrice'] = self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Bond']==bond, 'PriceY'].iloc[0]
            self.EODPrices = self.th.positions['EODPrice'].copy()
            self.EODPrices.to_csv(savepath)
            self.th.positionsByISINBook[['SOD_Pos','PriceY','Qty']] = self.th.positionsByISINBook[['SOD_Pos','PriceY','Qty']].astype(float)
        else:
            self.EODPrices = pandas.read_csv(savepath, header=None, index_col=0, names=['EODPrice'], squeeze=True)
            self.th.positions['EODPrice'] = self.EODPrices
            self.th.positionsByISINBook = pandas.read_csv(TEMPPATH+'SOD_risk_prices.csv', index_col=0) #to pick up the prices
        self.EODPrices.name = 'EODPrice'
        del self.th.positionsByISINBook['EODPrice']
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.EODPrices, on='Bond')
        self.th.positionsByISINBook['USDQty'] = self.th.positionsByISINBook.apply(lambda row:row['Qty']/ccy.loc[row['CCY'],'2017'],axis=1)
        for issuer in self.riskFreeIssuers:
            self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Issuer']==issuer,'Risk'] = 0 # UST HAVE NO CREDIT RISK
        self.EODPricesFilled = True

    def onUpdateTree(self, message=None):#EVENT LISTENER
        self.treeRebuild()

    def treeRebuild(self):
        self.traded_bonds = self.th.df[self.th.df['Date']==todayDateSTR]['Bond'].drop_duplicates().dropna().copy()
        new_bonds = list(set(self.traded_bonds) - set(self.displayPositions.index))
        
        self.th.positions['EODPrice'] = self.EODPrices
        self.th.positions['EODPrice'].fillna(0.0, inplace=True)
        for bond in new_bonds:
            self.th.positions.loc[bond,'EODPrice'] = self.th.df[self.th.df['Bond']==bond].iloc[-1]['Price'] # we take the last traded price
        self.EODPrices = self.th.positions['EODPrice'].copy()
        if self.bdmReady:
            pass
        else:
            self.th.positionsByISINBook['PRINCIPAL_FACTOR'] = 1.0
            self.th.positionsByISINBook['RISK_MID'] = 0.0
            self.th.positionsByISINBook['SAVG'] = 0.0
            self.th.positionsByISINBook['IRRisk'] = 0.0
        
        self.th.positionsByISINBook['PriceT'] = self.th.positionsByISINBook['PriceT'].astype(float)#NEEDED OTHERWISE DEFAULTS TO int64
        for (i, row) in self.th.positionsByISINBook.iterrows():
            try:
                self.th.positionsByISINBook.at[i,'PriceT'] = self.bdm.df.at[row['Bond'], 'MID']
            except:
                self.th.positionsByISINBook.at[i,'PriceT'] = pandas.np.nan # for UST and unrecognized bonds
        riskFreeIsins = []
        for issuer in self.riskFreeIssuers:
            riskFreeIsins = riskFreeIsins + list(self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Issuer']==issuer,'ISIN'])
        #if len(riskFreeIsins) > 0:
        #    riskFreePrices = blpapiwrapper.simpleReferenceDataRequest(dict(zip(riskFreeIsins, map(lambda x:x + '@BGN Corp', riskFreeIsins))), 'PX_MID')
        #    for (i,row) in riskFreePrices.iterrows():
        #        self.th.positionsByISINBook.loc[self.th.positionsByISINBook['ISIN']==i,'PriceT'] = float(row['PX_MID'])
        self.th.positionsByISINBook.drop(['PRINCIPAL_FACTOR','RISK_MID','EODPrice', 'SAVG', 'IRRisk'], axis=1, inplace=True)
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.EODPrices, on='Bond')
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.bdm.df['PRINCIPAL_FACTOR'], on='Bond')
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.bdm.df['RISK_MID'], on='Bond')
        self.th.positionsByISINBook = self.th.positionsByISINBook.join(self.bdm.df['SAVG'], on='Bond')
        for issuer in self.riskFreeIssuers:
            #self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Issuer']==issuer,'RISK_MID'] = 0.0 # UST HAVE NO CREDIT RISK
            self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Issuer']==issuer,'PRINCIPAL_FACTOR'] = 1.0        
        self.th.positionsByISINBook[['PRINCIPAL_FACTOR','RISK_MID','SAVG']] = self.th.positionsByISINBook[['PRINCIPAL_FACTOR','RISK_MID','SAVG']].astype(float)
        self.th.positionsByISINBook['SODPnL'] = self.th.positionsByISINBook['SOD_Pos'] *  self.th.positionsByISINBook['PRINCIPAL_FACTOR'] * (self.th.positionsByISINBook['PriceT'] - self.th.positionsByISINBook['PriceY'])/100.
        self.updateNewTradesByISIN() # at that point prices and principal factors are ready already if self.bdmReady
        self.th.positionsByISINBook['SODPnL'].fillna(0.0, inplace = True) 
        self.th.positionsByISINBook['TradePnL'].fillna(0.0, inplace = True)
        self.th.positionsByISINBook['MK'].fillna(0.0, inplace = True)
        self.th.positionsByISINBook['TotalPnL'] = self.th.positionsByISINBook['SODPnL']/self.th.positionsByISINBook.apply(lambda row:ccy.loc[row['CCY'],'2017'],axis=1) + self.th.positionsByISINBook['TradePnL']/self.th.positionsByISINBook.apply(lambda row:ccy.loc[row['CCY'],'2016'],axis=1)
        self.th.positionsByISINBook['USDQty'] = self.th.positionsByISINBook.apply(lambda row:row['Qty']/ccy.loc[row['CCY'],'2017'],axis=1)
        self.th.positionsByISINBook['EODValue'] = self.th.positionsByISINBook['EODPrice']*self.th.positionsByISINBook['USDQty']/100.*(self.th.positionsByISINBook['PRINCIPAL_FACTOR'])
        self.th.positionsByISINBook['Risk'] = -self.th.positionsByISINBook['USDQty']*self.th.positionsByISINBook['RISK_MID']/10000
        self.th.positionsByISINBook['IRRisk'] = self.th.positionsByISINBook['Risk'] 
        for issuer in self.riskFreeIssuers:
            self.th.positionsByISINBook.loc[self.th.positionsByISINBook['Issuer']==issuer,'Risk'] = 0.0
        self.th.positionsByISINBook['NewTrades'] = self.th.positionsByISINBook['Qty']-self.th.positionsByISINBook['SOD_Pos']
        self.th.positionsByISINBook['NewTrades'].fillna(0, inplace=True)
        #self.th.positionsByISINBook['']
        #self.displayPositionsBook = self.th.positionsByISINBook
        self.displayGroupBook = self.th.positionsByISINBook.groupby(['Book','LongCountry','Issuer','Bond','Series']).sum() #NECESSARY
        pub.sendMessage('REDRAW_TREE', message=MessageContainer('empty'))
        #self.th.positionsByISINBook.to_csv(TEMPPATH+'test.csv')

    def updateNewTradesByISIN(self):
        #THERE SHOULD NOT BE MORE THAN ONE RECORD PER BOOK AND ISIN - THE KEY IS BOOK-ISIN
        self.th.positionsByISINBook = self.th.positionsByISINBook[self.th.positionsByISINBook['SOD_Pos']!=0].copy()
        self.new_trades = self.th.df[self.th.df['Date']==todayDateSTR].copy()
        self.new_trades['TradePnL'] = 0.0
        if self.bdmReady:
            self.new_trades = self.new_trades.join(self.bdm.df['MID'], on='Bond')
            riskFreeIsins = []
            for issuer in self.riskFreeIssuers:
                riskFreeIsins = riskFreeIsins + list(self.new_trades.loc[self.new_trades['Issuer']==issuer,'ISIN'])
            #if len(riskFreeIsins)>0:
            #    riskFreePrices = blpapiwrapper.simpleReferenceDataRequest(dict(zip(riskFreeIsins, map(lambda x:x + '@BGN Corp', riskFreeIsins))), 'PX_MID')
            #    for (i,row) in riskFreePrices.iterrows():
            #        self.new_trades.loc[self.new_trades['ISIN']==i,'MID'] = float(row['PX_MID'])#this works because bond name == isin for UST and bunds but it's not very clean
        self.positionDeltas = self.new_trades.groupby(['Book','ISIN'])[['Qty','MK']]
        reclist = []
        nkeylist = []
        for (k,grp) in self.positionDeltas:
            key = k[0] + '-' + k[1]
            if key in self.th.positionsByISINBook.index:
                self.th.positionsByISINBook.at[key,'Qty'] = self.th.positionsByISINBook.at[key,'SOD_Pos'] + grp['Qty'].sum()
                self.th.positionsByISINBook.at[key,'MK'] = grp['MK'].sum()
            else:
                lr = self.new_trades.loc[self.new_trades['ISIN']==k[1]].iloc[-1]#take the last trade -> ONLY FOR STATIC DATA
                bond = lr['Bond']
                try:
                    pf = self.bdm.df.at[bond,'PRINCIPAL_FACTOR']
                    r = self.bdm.df.at[bond,'RISK_MID']
                    savg = self.bdm.df.at[bond,'SAVG']
                except:
                    print key + ' is missing in the Pricer!!!'
                    pf = 1
                    r = 0
                    savg = 0
                lc = self.cntrymap.at[lr['Country'],'LongCountry']
                rg = lr['Region']
                pt = lr['Price']
                series = 'REGS' if k[1]==bonds.loc[bond,'REGS'] else '144A'
                rec = [bond,k[0],lr['CCY'],k[1],lr['Issuer'], lr['Country'],lc,0,series, grp['Qty'].sum(), grp['MK'].sum(), lr['Price'], pandas.np.nan, pf, r, savg, rg, pt]
                reclist.append(rec)
                nkeylist.append(key)
        if reclist != []:
            reclistdf = pandas.DataFrame(data=reclist, columns=['Bond','Book','CCY','ISIN','Issuer','Country','LongCountry','SOD_Pos', 'Series','Qty', 'MK', 'EODPrice', 'PriceY', 'PRINCIPAL_FACTOR','RISK_MID','SAVG','Region','PriceT'], index=nkeylist)
            self.th.positionsByISINBook = self.th.positionsByISINBook.append(reclistdf, verify_integrity=True)
        for (k,grp) in self.positionDeltas:#calculate trade pnl
            key = k[0] + '-' + k[1]
            idx = (self.new_trades['ISIN']==k[1]) & (self.new_trades['Book']==k[0])
            self.new_trades.loc[idx,'TradePnL'] = self.new_trades.loc[idx,'Qty']*(self.new_trades.loc[idx,'MID']-self.new_trades.loc[idx,'Price'])/100.
            try:
                self.th.positionsByISINBook.at[key,'TradePnL'] = self.th.positionsByISINBook.at[key,'PRINCIPAL_FACTOR'] * self.new_trades.loc[idx,'TradePnL'].sum()
            except:
                print 'error finding a price for ' + key
        #pass
        #self.th.positionsByISINBook.to_csv(TEMPPATH+'test.csv')
        #self.displayPositions.to_csv(TEMPPATH+'test2.csv')

