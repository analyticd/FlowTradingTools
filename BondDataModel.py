"""
Bond pricer - displays data from Bloomberg and Front, MVC architecture.
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Classes:
MessageContainer: simple wrapper
RFDdata: used to poll risk free prices every few minutes
BondDataModel: the main class, basically a huge table with data getting updated from Bloomberg in real time.
StreamWatcher: helper class to send analytics data (both real time price data and static data) to the BondDataModel

Functions:
getMaturityDate(): helper function to convert Bloomberg date format to datetime format
"""
import wx
from wx.lib.pubsub import pub

import pandas
import blpapiwrapper
import threading
import datetime
import os
import time
from win32api import GetUserName

from StaticDataImport import ccy, countries, bonds, TEMPPATH, bonduniverseexclusionsList, frontToEmail, SPECIALBONDS, SINKABLEBONDS, BBGHand, regsToBondName, bbgToBdmDic, PHPATH, traderLogins

class MessageContainer():
    def __init__(self,data):
        self.data = data

def getMaturityDate(d):
    # Function to parse maturity date in YYYY-MM-DD format. Override for perps
    try:
        output = datetime.datetime.strptime(d, '%Y-%m-%d')
    except:
        output = datetime.datetime(2049, 12, 31)
    return output


class RFdata(wx.Timer):
    def __init__(self, secs, req, bdm):
        wx.Timer.__init__(self)
        self.bdm = bdm
        self.req = req                     
        self.Bind(wx.EVT_TIMER, self.refreshRFBonds)
        self.Start(1000*secs, oneShot = False)

    def refreshRFBonds(self,event):
        self.req.get()
        out = self.req.output.astype(float)
        for (isinkey, data) in out.iterrows():
            self.bdm.updatePrice(isinkey, 'ALL', data, 'ANALYTICS')
        # print 'Refreshed RF bonds'


class BDMdata(wx.Timer):
    def __init__(self, secs, bdm):
        wx.Timer.__init__(self)
        self.bdm = bdm
        self.dic = pandas.Series((self.bdm.df['ISIN'] + '@BGN Corp').values, index=self.bdm.df.index).to_dict()
        self.Bind(wx.EVT_TIMER, self.refreshBDMPrice)
        self.Start(1000*secs, oneShot = False)

    def refreshBDMPrice(self,event):
        out = blpapiwrapper.simpleReferenceDataRequest(self.dic,'PX_MID')['PX_MID']
        self.bdm.lock.acquire()
        self.bdm.df['BGN_MID'] = out.astype(float)
        self.bdm.lock.release()
        pub.sendMessage('BGN_PRICE_UPDATE', message=MessageContainer('empty'))


class BDMEODsave(wx.Timer):
    def __init__(self, bdm):
        wx.Timer.__init__(self)
        self.bdm = bdm
        self.Bind(wx.EVT_TIMER, self.saveFile)
        now = datetime.datetime.now()
        fivepm = now.replace(hour=17, minute = 0, second = 0)
        now_to_five_pm = (fivepm - now).total_seconds()
        self.Start(1000*now_to_five_pm, oneShot = True)

    def saveFile(self, event):
        self.bdm.firstPass()
        out = self.bdm.df[['ISIN', 'BOND', 'MID', 'YLDM', 'ZM', 'BGN_MID']].copy()
        out.set_index('ISIN', inplace=True)
        filename = 'bdm-' + datetime.datetime.today().strftime('%Y-%m-%d') + '-' + GetUserName() + '.csv'
        out.to_csv(PHPATH + filename)


class BondDataModel():
    """BondDataModel class : Class to define the bond data model

    Attributes:
    self.parent = parent frame (Wx.Frame object)
    self.dtToday : datetime.datetime object for today 
    self.dtYesterday : datetime.datetime object for yesterday 
    self.dtLastWeek : datetime.datetime object for last week 
    self.dtLastMonth : datetime.datetime object for last month
    self.mainframe : FlowTradingGUI > MainForm class instance
    self.th : trade history data. (defaults to None if mainframe is not specified. 
                                    This is to allow Pricer to be launched independently without having to connect to Front)
    self.df : pandas.DataFrame consisting of all the bonds' information
    self.USDswapRate : Interpolated US Swap rates
    self.CHFswapRate : Interpolated CHF Swap rates 
    self.EURswapRate : Interpolated EUR Swap rates
    self.CNYswapRate : Interpolated CNY Swap rates 

    Methods:
    __init__()
    reduceUniverse()
    fillPositions()
    updatePrice()
    updateStaticAnalytics()
    updateCell()
    updatePositions()
    startUpdates()
    firstPass()
    reOpenConnection()
    refreshSwapRates()
    fillHistoricalPricesAndRating()
    updateBenchmarks()
    """
    def __init__(self, parent, mainframe=None):
        """
        Keyword arguments:
        parent : parent frame (Wx.Frame object)
        mainframe : FlowTradingGUI > MainForm class instance (defaults to [] if not specified)
        """
        self.parent = parent
        self.mainframe = mainframe
        self.th = None if mainframe is None else mainframe.th

        self.dtToday = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        _offsets = (3, 1, 1, 1, 1, 1, 2)
        self.dtYesterday = self.dtToday - datetime.timedelta(days=_offsets[self.dtToday.weekday()])
        self.dtLastWeek = self.dtToday - datetime.timedelta(days=7)
        dtTemp = self.dtToday - datetime.timedelta(days=29)
        self.dtLastMonth = dtTemp - datetime.timedelta(days=_offsets[dtTemp.weekday()])

        # Static columns either in bonduniverse or directly derived from it
        colsDescription = ['ISIN', 'BOND', 'SERIES', 'CRNCY', 'MATURITY', 'COUPON', 'AMT_OUTSTANDING', 'SECURITY_NAME',
                           'INDUSTRY_GROUP', 'CNTRY_OF_RISK', 'TICKER', 'MATURITYDT']
        # these columns will feed from Bloomberg (or Front) and be regenerated only once
        colsPriceHistory = ['P1DFRT', 'P1D', 'P1W', 'P1M', 'Y1D', 'Y1W', 'Y1M', 'SAVG', 'ISP1D','ISP1W','ISP1M','INTSWAP1D','INTSWAP1W','INTSWAP1M', 'PRINCIPAL_FACTOR']
        # these will feed from Bloomberg only once
        colsRating = ['SNP', 'MDY', 'FTC']
        colsAccrued = ['ACCRUED', 'D2CPN']
        # these columns will feed from Bloomberg (or Front) and be regenerated all the time
        colsPrice = ['BID', 'ASK', 'MID', 'BID_SIZE', 'ASK_SIZE', 'BGN_MID']
        colsAnalytics = ['YLDB', 'YLDA', 'YLDM', 'ZB', 'ZA', 'ZM','INTSWAP','RSI14','RISK_MID']
        colsChanges = ['DP1FRT', 'DP1D', 'DP1W', 'DP1M', 'DY1D', 'DY1W', 'DY1M','DISP1D','DISP1W','DISP1M']
        colsPosition = ['POSITION', 'REGS', '144A','MV','RISK']
        self.colsAll = colsDescription + colsPriceHistory + colsRating + colsAccrued + colsPrice + colsAnalytics + colsChanges + colsPosition  # +colsPricingHierarchy+colsUpdate

        self.df = pandas.DataFrame(columns=self.colsAll, index=bonds.index)
        # self.df.drop(bonduniverseexclusionsList,inplace=True)
        self.df['BOND'] = self.df.index
        self.df['ISIN'] = bonds['REGS']
        self.df['SERIES'] = 'REGS'
        self.gridList = []
        self.lock = threading.Lock()
        for c in list(set(colsDescription) & set(bonds.columns)):
            self.df[c] = bonds[c]
        self.df.rename(columns={'AMT_OUTSTANDING': 'SIZE'}, inplace=True)
        #self.df['SIZE'] = self.df['SIZE'].apply(lambda x: '{:,.0f}'.format(float(x) / 1000000) + 'm')
        self.df['MATURITYDT'] = self.df['MATURITY'].apply(getMaturityDate)
        self.df = self.df[self.df['MATURITYDT'] >= self.dtToday]
        self.df['MATURITY'] = self.df['MATURITYDT'].apply(lambda x: x.strftime('%d/%m/%y'))
        self.df['POSITION'] = 0
        pub.subscribe(self.updatePositions, "POSITION_UPDATE")
        self.bondList = []
        self.bbgPriceQuery = ['BID', 'ASK', 'YLD_CNV_BID', 'YLD_CNV_ASK', 'Z_SPRD_BID', 'Z_SPRD_ASK','RSI_14D', 'BID_SIZE', 'ASK_SIZE']
        self.bbgPriceSpecialQuery = ['BID', 'ASK', 'YLD_CNV_BID', 'YLD_CNV_ASK', 'OAS_SPREAD_BID', 'OAS_SPREAD_ASK','RSI_14D', 'BID_SIZE', 'ASK_SIZE']
        self.bbgPriceSinkableQuery = ['BID', 'ASK', 'YLD_CNV_BID', 'YLD_CNV_ASK', 'RSI_14D', 'BID_SIZE', 'ASK_SIZE']
        self.riskFreeIssuers = ['T', 'DBR', 'UKT', 'OBL']
        self.bbgPriceRFQuery = ['BID', 'ASK', 'BID_YIELD', 'ASK_YIELD']
        self.bbgSinkRequest = blpapiwrapper.BLPTS()
        pass

    def reduceUniverse(self):
        """Reduce the bond universe to bonds that are in any one grid
        """
        self.bondList = list(set([bond for grid in self.parent.gridList for bond in grid.bondList]))#set removes duplicates
        self.df = self.df.reindex(self.bondList)
        self.df = self.df[pandas.notnull(self.df['ISIN'])]
        self.rfbonds = list(self.df.loc[self.df['TICKER'].isin(self.riskFreeIssuers)].index)
        self.embondsisins = self.df.loc[~self.df['TICKER'].isin(self.riskFreeIssuers), 'ISIN']
        self.rfbondsisins = self.df.loc[self.df['TICKER'].isin(self.riskFreeIssuers), 'ISIN']

    def fillPositions(self):
        """Fills positions if trade history data is available
        """
        if self.th is not None:
            self.df['POSITION'] = self.th.positions['Qty']
            self.df['REGS'] = self.th.positions['REGS']
            self.df['144A'] = self.th.positions['144A']
            self.df['POSITION'].fillna(0, inplace=True)
            self.df['REGS'].fillna(0, inplace=True)
            self.df['144A'].fillna(0, inplace=True)
            self.df['RISK'] = -self.df['RISK_MID'] * self.df['POSITION'] / 10000.

    def updatePrice(self, isinkey, field, data, bidask):
        """
        Gets called by StreamWatcher. 
        Keyword arguments:
        isinkey : ISIN 
        field : field to update, not used
        data : data, a pandas Series
        bidask : 'BID' fetches new events from bloomberg. 'ANALYTICS', 'FIRSTPASS' or 'RTGACC' updates cells in grid.
        Importantly, there can be a 'BID' event without any data, so one needs to specifically call for the BID as well after an event.
        """
        isin = isinkey[0:12]
        bond = regsToBondName[isin]
        if bidask == 'BID':
            if bond in self.rfbonds:
                self.blptsAnalytics.get(isin + '@CBBT' + ' Corp', self.bbgPriceRFQuery)
            elif bond in SPECIALBONDS:
                self.blptsAnalytics.get(isin + BBGHand + ' Corp', self.bbgPriceSpecialQuery)
            else:
                try:
                    self.blptsAnalytics.get(isin + BBGHand + ' Corp', self.bbgPriceQuery)
                except:
                    print 'error asking analytics for ' + bond
        elif bidask == 'RTGACC':
            for item, value in data.iteritems():
                self.updateCell(bond,bbgToBdmDic[item],value)
        else:#'ANALYTICS' or 'FIRSTPASS'
            data = data.astype(float)
            try:
                for item, value in data.iteritems():
                    self.updateCell(bond,bbgToBdmDic[item],value)
            except:
                print data
            if bond in SINKABLEBONDS:
                self.bbgSinkRequest.fillRequest(isin + ' Corp', ['YAS_ZSPREAD'], strOverrideField='YAS_BOND_PX', strOverrideValue=data['BID'])
                self.bbgSinkRequest.get()
                self.updateCell(bond, 'ZB', float(self.bbgSinkRequest.output.values[0,0]))
                self.bbgSinkRequest.fillRequest(isin + ' Corp', ['YAS_ZSPREAD'], strOverrideField='YAS_BOND_PX', strOverrideValue=data['ASK'])
                self.bbgSinkRequest.get()                
                self.updateCell(bond, 'ZA', float(self.bbgSinkRequest.output.values[0,0]))
            if bidask == 'ANALYTICS':
                self.updateStaticAnalytics(bond)

    def send_price_update(self, bonddata):
        pub.sendMessage('BOND_PRICE_UPDATE', message=MessageContainer(bonddata))

    def updateStaticAnalytics(self, bond):
        """Updates static analytics.
        """
        self.updateCell(bond, 'MID', (self.df.at[bond, 'BID'] + self.df.at[bond, 'ASK']) / 2.)
        self.updateCell(bond, 'DP1FRT', self.df.at[bond, 'MID'] - self.df.at[bond, 'P1DFRT'])       
        self.updateCell(bond, 'DP1D', self.df.at[bond, 'MID'] - self.df.at[bond, 'P1D'])
        self.updateCell(bond, 'DP1W', self.df.at[bond, 'MID'] - self.df.at[bond, 'P1W'])
        self.updateCell(bond, 'DP1M', self.df.at[bond, 'MID'] - self.df.at[bond, 'P1M'])
        self.updateCell(bond, 'YLDM', (self.df.at[bond, 'YLDB'] + self.df.at[bond, 'YLDA']) / 2.)
        self.updateCell(bond, 'DY1D', (self.df.at[bond, 'YLDM'] - self.df.at[bond, 'Y1D']) * 100)
        self.updateCell(bond, 'DY1W', (self.df.at[bond, 'YLDM'] - self.df.at[bond, 'Y1W']) * 100)
        self.updateCell(bond, 'DY1M', (self.df.at[bond, 'YLDM'] - self.df.at[bond, 'Y1M']) * 100)
        self.updateCell(bond, 'ZM', (self.df.at[bond, 'ZB'] + self.df.at[bond, 'ZA']) / 2.)
        self.updateCell(bond, 'DISP1D', (self.df.at[bond, 'ZM'] - self.df.at[bond, 'ISP1D']))
        self.updateCell(bond, 'DISP1W', (self.df.at[bond, 'ZM'] - self.df.at[bond, 'ISP1W']))
        self.updateCell(bond, 'DISP1M', (self.df.at[bond, 'ZM'] - self.df.at[bond, 'ISP1M']))
        pub.sendMessage('BOND_PRICE_UPDATE', message=MessageContainer(self.df.loc[bond]))

    def updateCell(self, bond, field, value):
        # Thread safe implementation to update individual cells
        self.lock.acquire()
        self.df.at[bond, field] = value
        self.lock.release()

    def updatePositions(self, message=None):
        # Thread safe implementation to update positions
        self.lock.acquire()
        self.df['REGS'] = message.data['REGS']
        self.df['144A'] = message.data['144A']
        self.df['REGS'].fillna(0, inplace=True)
        self.df['144A'].fillna(0, inplace=True)
        self.df['POSITION'] = self.df['REGS'] + self.df['144A']
        self.df['RISK'] = -self.df['RISK_MID'] * self.df['POSITION'] / 10000.
        self.lock.release()

    def startUpdates(self):
        """Starts live feed from Bloomberg.
        """
        # Analytics stream
        self.blptsAnalytics = blpapiwrapper.BLPTS()
        self.streamWatcherAnalytics = StreamWatcher(self, 'ANALYTICS')
        self.blptsAnalytics.register(self.streamWatcherAnalytics)
        # Price change subscription
        self.streamWatcherBID = StreamWatcher(self,'BID')
        self.bbgstreamBIDEM = blpapiwrapper.BLPStream(list((self.embondsisins + BBGHand + ' Corp').astype(str)), 'BID', 0)
        self.bbgstreamBIDEM.register(self.streamWatcherBID)
        self.bbgstreamBIDEM.start()
        # Risk free bonds: no streaming as too many updates - poll every 10 minutes
        rfRequest = blpapiwrapper.BLPTS(list((self.rfbondsisins + '@CBBT' + ' Corp').astype(str)), self.bbgPriceRFQuery)
        self.RFtimer = RFdata(600, rfRequest, self)
        self.BDMdata = BDMdata(1800, self) #30 MINUTES
        self.BDMEODsave = BDMEODsave(self)

    def firstPass(self, priorityBondList=[]):
        """Loads initial data upon start up. After downloading data on first pass, function will check for bonds
        in SPECIALBONDS and will overwrite downloaded data with new set of data. 

        Keyword arguments:
        priortyBondList : priorty bonds to be updated (defaults to [] if not specified)
        """
        self.lastRefreshTime = datetime.datetime.now()
        if priorityBondList == []:
            emptyLines = list(self.df.index)
            isins = self.embondsisins + BBGHand + ' Corp'
        else:
            emptyLines = priorityBondList
            isins = self.df.loc[priorityBondList, 'ISIN'] + BBGHand + ' Corp'
        isins = list(isins.astype(str))
        blpts = blpapiwrapper.BLPTS(isins, self.bbgPriceQuery)
        blptsStream = StreamWatcher(self,'FIRSTPASS')
        blpts.register(blptsStream)
        blpts.get()
        blpts.closeSession()

        isins = self.rfbondsisins + ' @CBBT Corp'
        isins = list(isins.astype(str))
        blpts = blpapiwrapper.BLPTS(isins, self.bbgPriceRFQuery)
        blptsStream = StreamWatcher(self, 'FIRSTPASS')
        blpts.register(blptsStream)
        blpts.get()
        blpts.closeSession()

        specialBondList = list(set(emptyLines) & set(SPECIALBONDS))
        specialIsins = map(lambda x:self.df.at[x,'ISIN'] + BBGHand + ' Corp',specialBondList)
        blpts = blpapiwrapper.BLPTS(specialIsins, self.bbgPriceSpecialQuery)
        specialbondStream = StreamWatcher(self,'FIRSTPASS')
        blpts.register(specialbondStream)
        blpts.get()
        blpts.closeSession()

        for bond in emptyLines:
            self.updateStaticAnalytics(bond)  # This will update benchmarks and fill grid. Has to be done here so all data for benchmarks is ready.

    def reOpenConnection(self):
        """Reopens bloomberg connection. Function is called when the 'Restart Bloomberg Connection' button from the pricer frame is clicked
        """
        self.blptsAnalytics.closeSession()
        self.blptsAnalytics = None
        self.bbgstreamBIDEM.closeSubscription()
        self.bbgstreamBIDEM = None
        self.streamWatcherBID = None
        self.streamWatcherAnalytics = None
        self.firstPass()
        self.startUpdates()

    def refreshSwapRates(self):
        """Refreshes the swap rates. Function is called when the 'Refresh Rates' button from the pricer menu is clicked.
        """
        self.firstPass()

    def fillHistoricalPricesAndRating(self):
        """Fill historical prices and ratings. Function is called when the pricer menu first launches. 
        """
        time_start = time.time()
        self.buildPriceHistory()
        savepath = TEMPPATH + 'bondhistoryrating.csv'
        #If bondhistoryratingUAT.csv doesn't exist, download data and write file.
        cols = ['SNP', 'MDY', 'FTC', 'P1D', 'P1W', 'P1M', 'Y1D', 'Y1W', 'Y1M', 'ACCRUED', 'D2CPN', 'SAVG', 'ISP1D', 'ISP1W', 'ISP1M', 'RISK_MID', 'PRINCIPAL_FACTOR', 'SIZE']
        if not (os.path.exists(savepath)) or datetime.datetime.fromtimestamp(
                os.path.getmtime(savepath)).date() < datetime.datetime.today().date():
            isins = self.df['ISIN'] + BBGHand + ' Corp'
            isins = list(isins.astype(str))

            ##
            flds = ['RTG_SP', 'RTG_MOODY', 'RTG_FITCH', 'INT_ACC', 'DAYS_TO_NEXT_COUPON', 'YRS_TO_SHORTEST_AVG_LIFE', 'RISK_MID', 'PRINCIPAL_FACTOR', 'AMT_OUTSTANDING']
            out = blpapiwrapper.simpleReferenceDataRequest(pandas.Series((self.df['ISIN'] + ' Corp').values, index=self.df.index).to_dict(),flds)[flds]
            #loop
            for f in flds:
                self.df[bbgToBdmDic[f]] = out[f]
            self.df['RISK_MID'].fillna(0, inplace=True)
            ##
            self.df.drop(['P1D', 'P1W', 'P1M', 'Y1D', 'Y1W', 'Y1M', 'ISP1D', 'ISP1W', 'ISP1M'], axis=1, inplace=True)
            dbPriceHistory = pandas.read_csv(PHPATH + 'dbPriceHistory.csv', index_col=0)
            dbYieldHistory = pandas.read_csv(PHPATH + 'dbYieldHistory.csv', index_col=0)
            dbSpreadHistory = pandas.read_csv(PHPATH + 'dbSpreadHistory.csv', index_col=0)
            hdt = []
            if self.dtYesterday.strftime('%Y%m%d') in dbPriceHistory.columns:
                hdt.append(self.dtYesterday.strftime('%Y%m%d'))
            else:
                self.df['P1D'] = pandas.np.nan
                self.df['Y1D'] = pandas.np.nan
                self.df['ISP1D'] = pandas.np.nan
            if self.dtLastWeek.strftime('%Y%m%d') in dbPriceHistory.columns:
                hdt.append(self.dtLastWeek.strftime('%Y%m%d'))
            else:
                self.df['P1W'] = pandas.np.nan
                self.df['Y1W'] = pandas.np.nan
                self.df['ISP1W'] = pandas.np.nan
            if self.dtLastMonth.strftime('%Y%m%d') in dbPriceHistory.columns:
                hdt.append(self.dtLastMonth.strftime('%Y%m%d'))
            else:
                self.df['P1M'] = pandas.np.nan
                self.df['Y1M'] = pandas.np.nan
                self.df['ISP1M'] = pandas.np.nan
            ohdt = [self.dtYesterday.strftime('%Y%m%d'), self.dtLastWeek.strftime('%Y%m%d'), self.dtLastMonth.strftime('%Y%m%d')]
            self.df = self.df.join(dbPriceHistory[hdt], on='ISIN')
            self.df.rename(columns={ohdt[0]:'P1D', ohdt[1]:'P1W', ohdt[2]:'P1M'}, inplace=True)
            self.df = self.df.join(dbYieldHistory[hdt], on='ISIN')
            self.df.rename(columns={ohdt[0]:'Y1D', ohdt[1]:'Y1W', ohdt[2]:'Y1M'}, inplace=True)
            self.df = self.df.join(dbSpreadHistory[hdt], on='ISIN')
            self.df.rename(columns={ohdt[0]:'ISP1D', ohdt[1]:'ISP1W', ohdt[2]:'ISP1M'}, inplace=True)

            self.df[cols].to_csv(savepath)
            self.df['ACCRUED'] = self.df['ACCRUED'].apply(lambda x: '{:,.2f}'.format(float(x)))
            self.df['D2CPN'].fillna(-1, inplace=True)
            self.df['D2CPN'] = self.df['D2CPN'].astype(int)
            self.df[['RISK_MID','PRINCIPAL_FACTOR','SIZE']] = self.df[['RISK_MID','PRINCIPAL_FACTOR','SIZE']].astype(float)
            self.df[['SNP', 'MDY', 'FTC']] = self.df[['SNP', 'MDY', 'FTC']].fillna('NA')  # ,'ACCRUED','D2CPN'
            self.df[['SNP', 'MDY', 'FTC', 'ACCRUED']] = self.df[['SNP', 'MDY', 'FTC', 'ACCRUED']].astype(str)

        #Otherwise, load and read from file.
        else:
            print 'Found existing file from today'
            df = pandas.read_csv(savepath, index_col=0)
            self.df[cols] = df[cols]
            self.df[['RISK_MID','PRINCIPAL_FACTOR','SIZE','SAVG', 'ISP1D','ISP1W','ISP1M']] = self.df[['RISK_MID','PRINCIPAL_FACTOR','SIZE','SAVG', 'ISP1D','ISP1W','ISP1M']].astype(float)
            self.df[['SNP', 'MDY', 'FTC']] = self.df[['SNP', 'MDY', 'FTC']].astype(str)
            self.df['ACCRUED'].fillna(-1,inplace=True)#HACK SO NEXT LINE DOESN'T BLOW UP - WE DON'T WANT TO PUT 0 THERE!
            self.df['ACCRUED'] = self.df['ACCRUED'].astype(float)
            self.df['ACCRUED'] = self.df['ACCRUED'].apply(lambda x: '{:,.2f}'.format(float(x)))
            self.df['D2CPN'].fillna(-1, inplace=True)#HACK SO NEXT LINE DOESN'T BLOW UP - WE DON'T WANT TO PUT 0 THERE!
            self.df['D2CPN'] = self.df['D2CPN'].astype(int)          

        print 'History fetched in: ' + str(int(time.time() - time_start)) + ' seconds.'

    def updateBenchmarks(self):
        for grid in self.gridList:
            grid.updateBenchmarks()

    def buildPriceHistory(self):
        self.dbPriceHistory = pandas.read_csv(PHPATH+'dbPriceHistory.csv', index_col=0)
        self.dbYieldHistory = pandas.read_csv(PHPATH+'dbYieldHistory.csv', index_col=0)
        self.dbSpreadHistory = pandas.read_csv(PHPATH+'dbSpreadHistory.csv', index_col=0)
        todayStr = datetime.date.today().strftime('%Y%m%d')
        if not todayStr in self.dbPriceHistory.columns:
            last_existing_date = datetime.datetime.strptime(max(self.dbPriceHistory.columns),'%Y%m%d').date()
            start_date = last_existing_date + datetime.timedelta(1)
            end_date = datetime.date.today()
            day_count = (end_date - start_date).days # until yesterday
            for single_date in (start_date + datetime.timedelta(n) for n in range(day_count)):
                single_date_str = single_date.strftime('%Y-%m-%d')
                filenames = []
                isSuccess = False
                for trader in traderLogins:
                    fp = PHPATH + 'bdm-' + single_date_str + '-' + trader + '.csv'
                    if os.path.isfile(fp):
                        isSuccess = True
                        break
                if not isSuccess:
                    continue
                df = pandas.read_csv(fp, index_col=0)
                self.dbPriceHistory = pandas.concat([self.dbPriceHistory,df['MID']], axis=1)
                self.dbYieldHistory = pandas.concat([self.dbYieldHistory,df['YLDM']], axis=1)
                self.dbSpreadHistory = pandas.concat([self.dbSpreadHistory,df['ZM']], axis=1)
                single_date_str_short = single_date.strftime('%Y%m%d')
                self.dbPriceHistory.rename(columns={'MID':single_date_str_short}, inplace=True)
                self.dbYieldHistory.rename(columns={'YLDM':single_date_str_short}, inplace=True)
                self.dbSpreadHistory.rename(columns={'ZM':single_date_str_short}, inplace=True)
            self.dbPriceHistory.to_csv(PHPATH + 'dbPriceHistory.csv')
            self.dbYieldHistory.to_csv(PHPATH + 'dbYieldHistory.csv')
            self.dbSpreadHistory.to_csv(PHPATH + 'dbSpreadHistory.csv')
        else:
            pass
        pass


class StreamWatcher(blpapiwrapper.Observer):
    """StreamWatcher class : Class to stream and update analytic data from Bloomberg
    BID keyword for watching events, ANALYTICS to get everything once event triggered, FIRSTPASS for first pass, RTGACC for ratings
    """
    def __init__(self, bdm, bidask='BID'):
        self.bdm = bdm
        self.bidask = bidask

    def update(self, *args, **kwargs):
        if kwargs['field'] == 'ALL':
            self.bdm.updatePrice(kwargs['security'], kwargs['field'], kwargs['data'], self.bidask)

