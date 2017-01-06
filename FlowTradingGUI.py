"""
Main GUI to run various tools for Credit Flow Trading desk.
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2016 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Classes:
ResultEvent
TradeHistoryThread
TodayTradesThread
BuildModelPortfolioThread
RedirectText
MainForm


Functions:
EVT_RESULT_ID()
pydate2wxdate()
wxdate2pydate()
"""

import sys
import wx
from wx.lib.wordwrap import wordwrap
import pandas
import datetime
import subprocess
import pythoncom
from threading import Thread
from guiWidgets import *

from wx.lib.pubsub import pub

from win32api import GetUserName
import BondTools
from BondTools import ChartEngine
from BondTools import ChartTypes
from TradeHistoryAnalysis import TradeHistory # this is important so you can import/pickle the existing file
import ModelPortfolio
import FO_Toolkit
import RiskTreeView
import FrontPnL
import BondDataModel
import Pricer
from RiskTreeManager import RiskTreeManager
import ma_analysis
import time
# import mpfiPricer
from StaticDataImport import APPPATH, TEMPPATH, bonds, traderLogins
from ChartingPanel import ChartingPanel

pandas.set_option('display.max_columns', 500)
pandas.set_option('display.max_rows', 500)
pandas.set_option('display.width', 1000)


class MessageContainer():
    def __init__(self,data):
        self.data = data


# ##THREADING##
# ######################################################################## 
# Define notification event for thread completion
EVT_RESULT_ID = wx.NewId()
 
def EVT_RESULT(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, EVT_RESULT_ID, func)
 
# class ResultEvent(wx.PyEvent):
#     """Simple event to carry arbitrary result data."""
#     def __init__(self, data):
#         """Init Result Event."""
#         wx.PyEvent.__init__(self)
#         self.SetEventType(EVT_RESULT_ID)
#         self.data = data
 
# class TradeHistoryThread(Thread):
#     """Test Worker Thread Class."""
#     def __init__(self, wxObject, forceRebuild=False):
#         """Init Worker Thread Class."""
#         Thread.__init__(self)
#         self.wxObject = wxObject
#         self.forceRebuild=forceRebuild
#         self.start()    # start the thread
#     def run(self):
#         """Run Worker Thread."""
#         # This is the code executing in the new thread.
#         self.wxObject.buildTradeHistory(self.forceRebuild)
#         wx.PostEvent(self.wxObject, ResultEvent('Ready'))
#         pub.sendMessage('TRADE_HISTORY_READY', message=MessageContainer('empty'))

# class MarketAxessThread(Thread):
#     """Test Worker Thread Class."""
#     def __init__(self, wxObject, forceRebuild=False):
#         """Init Worker Thread Class."""
#         Thread.__init__(self)
#         self.wxObject = wxObject
#         self.forceRebuild=forceRebuild
#         self.start()    # start the thread
#     def run(self):
#         """Run Worker Thread."""
#         # This is the code executing in the new thread.
#         self.wxObject.buildMarketAxess(self.forceRebuild)
#         wx.PostEvent(self.wxObject, ResultEvent('Ready'))
#         pub.sendMessage('MARKET_AXESS_READY', message=MessageContainer('empty'))

##################################################################
class TodayTradesThread(Thread):
    """Test Worker Thread Class."""
    def __init__(self, wxObject):
        """Init Worker Thread Class."""
        Thread.__init__(self)
        #pythoncom.CoInitialize()
        self.wxObject = wxObject
        self.start()    # start the thread
    def run(self):
        """Run Worker Thread."""
        # This is the code executing in the new thread.
        self.wxObject.onTodayTradesSteps()
        pub.sendMessage('POSITION_UPDATE', message=MessageContainer(self.wxObject.th.positions))
##################################################################
class BuildModelPortfolioThread(Thread):
    """Test Worker Thread Class."""
    def __init__(self, wxObject):
        """Init Worker Thread Class."""
        Thread.__init__(self)
        #pythoncom.CoInitialize()
        self.wxObject = wxObject
        self.start()    # start the thread
    def run(self):
        """Run Worker Thread."""
        # This is the code executing in the new thread.
        self.wxObject.onBuildModelPortfolio()
        wx.PostEvent(self.wxObject, ResultEvent('Ready'))
        pub.sendMessage('MODEL_PORTFOLIO_READY', message=MessageContainer('empty'))

##################################################################
class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl
 
    def write(self,string):
        self.out.WriteText(string)

#def write(self, string):
#    wx.CallAfter(self.out.WriteText, string)
##################################################################

def pydate2wxdate(date):
    """Function to convert datetime.datetime to wx.datetime format 
    """
    assert isinstance(date, (datetime.datetime, datetime.date))
    tt = date.timetuple()
    dmy = (tt[2], tt[1]-1, tt[0])
    return wx.DateTimeFromDMY(*dmy)
 
def wxdate2pydate(date):
    """Function to convert wx.datetime to datetime.datetime format
    """
    assert isinstance(date, wx.DateTime)
    if date.IsValid():
        ymd = map(int, date.FormatISODate().split('-'))
        return datetime.date(*ymd)
    else:
        return None
##################################################################

##################################################################
         
class MainForm(wx.Frame):
    """
    Main frame 

    Attributes:

    Methods:
    __init__()

    ---Threading--- 
    updateTradeHistoryReady()
    onTestHistoryBuildItem()

    ---Generic Dialog Boxes---
    comboQuery()
    multipleComboQuery()
    textQuery()
    onClearLogButton()
    buildTradeHistory()
    createKeyLists()
    buildRiskPanel()
    checkModelPortfolio()

    ---File Actions---
    onAbout()
    onExit()

    ---Pricer Actions---
    onLaunchPricer()

    ---Trade History Actions---
    onBondQuery()
    onQuickBondQuery()
    onRiskTreeQuery()
    onBondQuerySub()
    onClientQuery()
    onSalesPersonQuery()
    onIssuerQuery()
    onCountryQuery()
    onAdvancedQuery()
    onMonthlyQuery()
    onClientTradingReport()
    onTestHistoryBuildItem()

    ---Performance Actions---
    onBenchmarkBondsVsEMBI()
    onAfricanBondsVsAfricaIndex()
    onAfricaWeekly()

    ---Model Portfolio---
    onBuildModelPortfolio()
    onPerformanceChartModelPortfolio()
    onPrintModelPortfolio()
    onSendModelPortfolioEmail()

    ---Chart Actions---
    onPlotBondSpreadGroup()
    onCreateBondSpreadPDFItem()
    onPlotYTDMinMaxItem()
    onPlotYTDPerformance()

    ---Front Actions---
    onLogInFront()
    onTodayTradesSteps()
    onTodayTrades()
    onOpenRepos()
    rebuildDailyPnL()
    rebuildLivePnL()
    onDailyPnL()
    onDailyPnLTH()

    ---Administration Actions---
    onUpdateBondUniverse()
    onNewClientReport()
    onRegs144aReport()
    onHighSCCheckItem()
    onForceRebuildTradeHistory()
    onBuildModelPortfolioButton()
    """
 
    def __init__(self):
        """
        We have two different environments - one for traders, one for sales
        """
        self.isTrader = GetUserName() in traderLogins
        wx.Frame.__init__(self, None, wx.ID_ANY, "Flow Trading Tools",size=(1200,900))
        favicon = wx.Icon(APPPATH+'pinacolada.ico', wx.BITMAP_TYPE_ICO, 32,32)
        wx.Frame.SetIcon(self,favicon)
        self.Centre()

        self.modelPortfolioLoaded = False
        self.embiZscores = None
        self.africaZscores = None
        self.todayDT = datetime.datetime.now()
        self.connectedToFront = False

        # Setting up the menu.
        fileMenu = wx.Menu()
        #pricerMenu = wx.Menu()
        tradeHistoryMenu = wx.Menu()
        modelPortfolioMenu = wx.Menu()
        adminMenu = wx.Menu()

        self.Bind(wx.EVT_CLOSE, self.onExit)


        ############PREATE MENUS############
        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        launchPricerItem = fileMenu.Append(wx.ID_ANY,'Launch &Pricer')
        aboutItem = fileMenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        fileMenu.AppendSeparator()
        exitItem = fileMenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        tradeHistoryMenuBondQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Bond query")
        tradeHistoryMenuQuickBondQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Quick bond query     Ctrl+B")
        tradeHistoryMenuClientQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Client query")
        tradeHistoryMenuSalesPersonQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Salesperson query")
        tradeHistoryMenuIssuerQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Issuer query")
        tradeHistoryMenuCountryQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Country query")
        tradeHistoryMenu.AppendSeparator()
        tradeHistoryMenuAdvancedQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Advanced query")
        tradeHistoryMenuMonthlyQueryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Monthly query")
        tradeHistoryMenu.AppendSeparator()
        clientTradingReportItem=tradeHistoryMenu.Append(wx.ID_ANY,"Client trading &report")

        buildModelPortfolioItem=modelPortfolioMenu.Append(wx.ID_ANY,"&Build")
        printModelPortfolioItem=modelPortfolioMenu.Append(wx.ID_ANY,"&Text output")
        performanceChartModelPortfolioItem=modelPortfolioMenu.Append(wx.ID_ANY,"&Performance chart")
        sendModelPortfolioEmail=modelPortfolioMenu.Append(wx.ID_ANY,"&Send email")

        openRepos = adminMenu.Append(wx.ID_ANY,"&Open repos")
        adminMenuUpdateBondUniverseItem=adminMenu.Append(wx.ID_ANY,"&Update BondUniverse file")
        highSCCheckItem=adminMenu.Append(wx.ID_ANY,"&High SC check")
        newClientReportItem=adminMenu.Append(wx.ID_ANY,"&New client report")
        regs144aReportItem=adminMenu.Append(wx.ID_ANY,"&REGS/144A report")
        forceRebuildTradeHistoryItem=tradeHistoryMenu.Append(wx.ID_ANY,"&Force rebuild trade history")
        africaWeeklyItem = adminMenu.Append(wx.ID_ANY,"Plot Africa weekly")
        ceeWeeklyItem = adminMenu.Append(wx.ID_ANY,"Plot CEE weekly")
        cisWeeklyItem = adminMenu.Append(wx.ID_ANY,"Plot CIS weekly")
        eurozoneWeeklyItem = adminMenu.Append(wx.ID_ANY,"Plot Eurozone weekly")
        maDataReportItem = adminMenu.Append(wx.ID_ANY,"Daily MA report")

        ############CREATE THE MENUBAR############
        self.menuBar = wx.MenuBar()
        self.menuBar.Append(fileMenu,"&File") 
        self.menuBar.Append(tradeHistoryMenu,"&Trade History") 
        self.menuBar.Append(modelPortfolioMenu,"&Model Portfolio") 
        self.menuBar.Append(adminMenu,"&Administration") 
        self.SetMenuBar(self.menuBar)  

        ############ASSIGN ACTIONS############
        self.Bind(wx.EVT_MENU,self.onLaunchPricer,launchPricerItem)        
        self.Bind(wx.EVT_MENU,self.onAbout,aboutItem)
        self.Bind(wx.EVT_MENU,self.onExit,exitItem)

        self.Bind(wx.EVT_MENU,self.onBondQuery,tradeHistoryMenuBondQueryItem)
        self.Bind(wx.EVT_MENU,self.onQuickBondQuery,tradeHistoryMenuQuickBondQueryItem)
        self.Bind(wx.EVT_MENU,self.onClientQuery,tradeHistoryMenuClientQueryItem)
        self.Bind(wx.EVT_MENU,self.onSalesPersonQuery,tradeHistoryMenuSalesPersonQueryItem)
        self.Bind(wx.EVT_MENU,self.onIssuerQuery,tradeHistoryMenuIssuerQueryItem)
        self.Bind(wx.EVT_MENU,self.onCountryQuery,tradeHistoryMenuCountryQueryItem)
        self.Bind(wx.EVT_MENU,self.onAdvancedQuery,tradeHistoryMenuAdvancedQueryItem)
        self.Bind(wx.EVT_MENU,self.onMonthlyQuery,tradeHistoryMenuMonthlyQueryItem)
        self.Bind(wx.EVT_MENU,self.onClientTradingReport,clientTradingReportItem)

        self.Bind(wx.EVT_MENU,self.onAfricaWeekly, africaWeeklyItem)
        self.Bind(wx.EVT_MENU,self.onCeeWeekly, ceeWeeklyItem)
        self.Bind(wx.EVT_MENU,self.onCisWeekly, cisWeeklyItem)
        self.Bind(wx.EVT_MENU,self.onEurozoneWeekly, eurozoneWeeklyItem)
        self.Bind(wx.EVT_MENU,self.onMaDataReportItem, maDataReportItem)

        self.Bind(wx.EVT_MENU,self.onBuildModelPortfolioButton,buildModelPortfolioItem)
        self.Bind(wx.EVT_MENU,self.onPrintModelPortfolio,printModelPortfolioItem)
        self.Bind(wx.EVT_MENU,self.onPerformanceChartModelPortfolio,performanceChartModelPortfolioItem)
        self.Bind(wx.EVT_MENU,self.onSendModelPortfolioEmail,sendModelPortfolioEmail)

        self.Bind(wx.EVT_MENU,self.onOpenRepos,openRepos)
        self.Bind(wx.EVT_MENU,self.onUpdateBondUniverse,adminMenuUpdateBondUniverseItem)
        self.Bind(wx.EVT_MENU,self.onNewClientReport,newClientReportItem)
        self.Bind(wx.EVT_MENU,self.onRegs144aReport,regs144aReportItem)
        self.Bind(wx.EVT_MENU,self.onHighSCCheckItem,highSCCheckItem)
        self.Bind(wx.EVT_MENU,self.onForceRebuildTradeHistory,forceRebuildTradeHistoryItem)

         ############CREATE PANEL AND BUTTONS############
        self.panel = wx.Panel(self, wx.ID_ANY)

        ############CREATE TABS############
        self.notebook = wx.Notebook(self.panel)
        self.tabLogs = wx.Panel(parent=self.notebook)
        self.notebook.AddPage(self.tabLogs, "Logs")

        self.log = wx.TextCtrl(self.tabLogs, wx.ID_ANY, size=(300,300), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.redirLogBox=RedirectText(self.log)         # redirect text here
        sys.stdout=self.redirLogBox
        self.log.SetFont(wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier'))
        sizerLogH = wx.BoxSizer()
        sizerLogH.Add(self.log,proportion=1,flag=wx.EXPAND)
        sizerlogV = wx.BoxSizer(wx.VERTICAL)
        sizerlogV.Add(sizerLogH,proportion=1,flag=wx.EXPAND)
        self.tabLogs.SetSizerAndFit(sizerlogV)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.notebook, 1, wx.ALL|wx.EXPAND, 5)
        self.panel.SetSizer(self.sizer)
        self.Layout()
 
        ############ACCELERATORS############
        xit_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onQuickBondQuery, id=xit_id)
        yit_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onRiskTreeQuery, id=yit_id)
        self.accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('B'), xit_id),(wx.ACCEL_CTRL, ord('F'), yit_id)])
        self.SetAcceleratorTable(self.accel_tbl)

        try:
            self.buildTradeHistory(False)
        except:
            print 'error building Trade History'
        try:
            self.buildMarketAxess(False)
        except:
            print 'error building MarketAxess history'

        #############Disable functions if dealing with a salesperson#############
        if not self.isTrader:
            self.menuBar.Remove(self.menuBar.FindMenu("&Administration"))

        print 'Building tabs, please wait...'
        wx.CallAfter(self.buildRiskPanel)

    ############GENERIC DIALOG BOXES############
    def comboQuery(self, event, title,question,choices):
        """Function to create combo dialog

        Keyword arguments:
        title : title of combo box 
        question : question
        choices : choices
        """
        dlg = ComboDialog(title,question,choices)
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_OK:
            data = dlg.comboBox1.GetValue()
            return data
        else:
            return ''

    def multipleComboQuery(self, event,myTitle,myQuestionList,myChoicesList):
        """function to show multiplpe combo dialog

        Keyword arguments:
        myTitle : title of combo box 
        myQuestionList : list of questions 
        myChoicesList : list of choices
        """
        dlg = MultipleComboDialog(myTitle,myQuestionList,myChoicesList)
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_OK:
            data = []
            cblist = dlg.comboBoxList
            for x in cblist:
                data.append(x.GetValue())
            return data
        else:
            return ''

    def textQuery(self,event,title,default=''):
        """
        Function to create wx.TextEntryDialog.
        """
        dlg = wx.TextEntryDialog(self, '',title,default, style=wx.OK)
        res = dlg.ShowModal()
        data = dlg.GetValue()
        dlg.Destroy()
        if res == wx.ID_OK:
            return data
        else:
            return ''

    def onClearLogButton(self, event):
        self.log.Clear()

    def buildTradeHistory(self,forceRebuild):
        """Function to build trade History 
        """
        print 'Building Trade History, please wait...'
        self.th = TradeHistory([],forceRebuild)
        self.bondlist = list(bonds.index)
        self.bondlist.sort()
        self.clientlist = self.th.counterpartyshortnamelist
        self.clientlist.sort()
        self.saleslist = self.th.ALLSALES
        self.issuerlist = list(bonds['TICKER'].drop_duplicates().astype(str))
        self.issuerlist.sort()
        self.countrylist = list(bonds['CNTRY_OF_RISK'].drop_duplicates().astype(str))
        self.countrylist.sort()
        #for i in range(1,self.menuBar.GetMenuCount()):
        #    self.menuBar.EnableTop(i,True)

    def buildMarketAxess(self,forceRebuild):
        """Function to build MarketAxess history 
        """
        print 'Building MarketAxess history, please wait...'
        self.ma = ma_analysis.FullMarketAxessData()
        print 'MarketAxess database ready'

    def buildRiskPanel(self):
        """Function to build Risk panel 
        """
        if self.isTrader:
            self.riskTreeManager = RiskTreeManager(self.th, self)
            self.tabRisk = RiskTabPanel(self.riskTreeManager,self.notebook,self)
            self.notebook.AddPage(self.tabRisk, "Risk by region")
            self.tabBookRiskPnL = BookRiskPnLTabPanel(self.riskTreeManager,self.notebook,self)
            self.notebook.AddPage(self.tabBookRiskPnL, "Risk by book")
            self.tabIRRiskPnL = IRRiskTabPanel(self.riskTreeManager,self.notebook,self)
            self.notebook.AddPage(self.tabIRRiskPnL, "Interest rate risk")
            self.tabTradeActivityGrid = TradeActivityTabPanel(self.th, self.notebook, self)
            self.notebook.AddPage(self.tabTradeActivityGrid, "Blotter")
        self.tabBondActivityMultiGrid = BondActivityTabPanel(self.th, self.ma, self.notebook, self)
        self.notebook.AddPage(self.tabBondActivityMultiGrid, "Bond activity")
        self.tabCharts = ChartingPanel(parent=self.notebook)
        self.notebook.AddPage(self.tabCharts, "Charts")
        wx.CallAfter(self.print_all_finished)

    def print_all_finished(self):
        print 'Ready to use'


    def checkModelPortfolio(self):
        """Function to check if the model portfolio has been loaded. If it hasn't, onBuildModelPortfolio is called to build
        the model portfolio.
        """
        if not(self.modelPortfolioLoaded):
            self.onBuildModelPortfolio()

    ############FILE ACTIONS############
    def onAbout(self, event):
        """Function to show the 'About' panel 
        """
        self.log.Clear()
        info = wx.AboutDialogInfo()
        info.Name = "Flow Trading Tools"
        info.Version = "5.1"
        info.Copyright = "(C) 2014-2016 Alexandre Almosni"
        info.Description = wordwrap("All data is indicative. Use at your own risk.",350, wx.ClientDC(self.panel))
        #info.WebSite = ("http://www.pythonlibrary.org", "My Home Page")
        #info.Developers = ["Alexandre Almosni"]
        info.License = wordwrap("Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0", 500, wx.ClientDC(self.panel))
        # Show the wx.AboutBox
        wx.AboutBox(info)

    def onExit(self,e):
        """Function to close the program.
        """
        if wx.MessageBox('This will also kill the Pricer.','Kill Flow Trading Tools?', wx.ICON_QUESTION | wx.YES_NO) == wx.YES:
            try:
                self.pricer.Destroy()
            except:
                pass
            self.Destroy()

    ############PRICER ACTIONS############
    def onLaunchPricer(self,event):
        if self.isTrader:
            self.tabRisk.onFillEODPrices(event)
        self.pricer = Pricer.PricerWindow(self)
        self.pricer.Show()
        pass

    ############TRADE HISTORY ACTIONS############
    def onBondQuery(self,event):
        """Function to query bond
        """
        bondname=self.comboQuery(event,'Bond query','Bond name?',self.bondlist)
        self.onBondQuerySub(bondname)
        pass

    def onQuickBondQuery(self,event):
        """Function for quick bond query. 
        """
        bondname = self.textQuery(event,'Bond name?').upper()
        if  (bondname in bonds.index):
            self.onBondQuerySub(bondname)
        else:
            print bondname + ' cannot be found.'

    def onRiskTreeQuery(self,event):
        """Function to query the risk tree. Function is called when user presses ctrl+f
        """
        # item = self.textQuery(event,'Bond or issuer name?').upper()
        # if  (item in bonds.index) or (item in self.issuerlist):
        #     self.tabRisk.onRiskTreeQuery(event, item)
        # else:
        #     self.notebook.SetSelection(0)
        #     print item + ' cannot be found.'
        item = self.textQuery(event,'Bond or issuer name?')
        self.tabRisk.onRiskTreeQuery(event, item)

    def onBondQuerySub(self,bondname):
        """Function to query the current position for the bond. Function is called by onBondQuery and onQuickBondQuery
        """
        #self.log.Clear()
        if self.isTrader:
            self.notebook.SetSelection(4)
        else:
            self.notebook.SetSelection(1)
        if self.isTrader:
            if bondname in self.th.positions.index:
                print 'Current position for ' + bondname + ': {:,.0f}'.format(self.th.positions.loc[bondname,'Qty'])
            else:
                print 'No current position in ' + bondname
            print ''
        self.tabBondActivityMultiGrid.fillGrid(bondname)
        self.th.simpleQuery('Bond',bondname)
        pass

    def onBondQuerySubOld(self,bondname):
        """Function to query the current position for the bond. Function is called by onBondQuery and onQuickBondQuery
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        if self.isTrader:
            if bondname in self.th.positions.index:
                print 'Current position for ' + bondname + ': {:,.0f}'.format(self.th.positions.loc[bondname,'Qty'])
            else:
                print 'No current position in ' + bondname
            print ''
        self.th.simpleQuery('Bond',bondname)
        pass

    def onClientQuery(self,event):
        """Function to query client. 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        clientname=self.comboQuery(event,'Client query','Client name?',self.clientlist)
        self.th.simpleQuery('Counterparty',clientname)

    def onSalesPersonQuery(self,event):
        """Function to query salesperson
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        salesperson=self.comboQuery(event,'Salesperson query','Salesperson name?',self.saleslist)
        self.th.simpleQuery('Sales',salesperson)

    def onIssuerQuery(self,event):
        """Function to query issuer
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        issuer=self.comboQuery(event,'Issuer query','Issuer ticker?',self.issuerlist)
        self.th.simpleQuery('Issuer',issuer)

    def onCountryQuery(self,event):
        """Function to query country 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        salesperson=self.comboQuery(event,'Country query','Country?',self.countrylist)
        self.th.simpleQuery('Country',salesperson)

    def onAdvancedQuery(self,event):
        """Function for Advanced query 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        adQ=AdvancedQuery(self,'Advanced query')
        res = adQ.ShowModal()
        adQ.Destroy()
        if res == wx.ID_OK:
            queryType=adQ.comboBox1.GetValue()
            if queryType=='Client':
                queryType='Counterparty'
            if queryType=='Salesperson':
                queryType='Sales'
            queryID=adQ.comboBox2.GetValue()
            startDate=wxdate2pydate(adQ.startcalendar.GetValue())
            endDate=wxdate2pydate(adQ.endcalendar.GetValue())
            self.th.advancedQuery(queryType,queryID,startDate,endDate)
        else:
            print ''

    def onMonthlyQuery(self,event):
        """Function for monthly query. 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        mthQ=MonthlyQuery(self,'Monthly query')
        res = mthQ.ShowModal()
        mthQ.Destroy()
        if res == wx.ID_OK:
            queryType=mthQ.comboBox1.GetValue()
            if queryType=='Client':
                queryType='Counterparty'
            if queryType=='Salesperson':
                queryType='Sales'
            queryID=mthQ.comboBox2.GetValue()
            self.th.reportMonthlyVolumeSC(queryType,queryID)
        else:
            print ''

    def onClientTradingReport(self,event):
        """Function to query client trading report 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        questionlist=['Select book:','Select year:','Select month:']
        books=['ALL']
        books.extend(self.th.LDNFLOWBOOKS)
        choiceList=[books,['2016','2015','2014','2013','2012','2011','2010','2009'],['Full Year','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']]
        data=self.multipleComboQuery(event,'Client trading report',questionlist,choiceList)
        book=data[0]
        year=int(data[1])
        month=[i for i,x in enumerate(choiceList[2]) if x == data[2]][0]
        self.th.clientTradingReport(year,month,book)
        pass

    #Threading
    def onTestHistoryBuildItem(self,event):
        TradeHistoryThread(self)
        pass

    ############PERFORMANCE ACTIONS############
    def onBenchmarkBondsVsEMBI(self,event):
        """Function to plot Benchmark Bonds vs EMBI 
        """
        self.log.Clear()
        bondlist=['ANGOL','ARMEN20','AZERBJ','BELRUS18','BRAZIL24','CHILE22','CHGRID23','COLOM24','CROATI24','ECUA24','EGYPT20','ESKOM23','EXIMBK23','GABON24','GEORG21','GHANA23','INDON24','IRAQ','IVYCST32','JAMAN25','KENINT24','KZOKZ23','LATVIA21','LEBAN26','LITHUN22','MEMATU','MEX23','MONGOL22','MOROC22','NGERIA23','OGIMK23','PANAMA26','PERTIJ23','PHILIP24','PKSTAN24','POLAND23','REPHUN23','REPNAM','ROMANI23','RUSSIA23','SENEGL21','SERBIA21','SLOVAK22','SOAF24','SRILAN22','TURKEY24','UKRAIN23','URUGUA24','VENZ38','ZAMBIN22']
        if self.embiZscores is None:
            x=ChartEngine(bondlist,ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,index='JPEIGLBL')
            self.embiZscores=x.output
        else:
            x=ChartEngine(bondlist,ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,source_data=self.embiZscores)
        print self.embiZscores
 
    def onAfricanBondsVsAfricaIndex(self,event):
        """Function to plot African bonds vs Africa Index 
        """
        self.log.Clear()
        bondlist=['ANGOL','ESKOM23','GABON24','GHANA23','IVYCST24','KENINT24','MEMATU','NGERIA23','REPNAM','SENEGL24','SOAF24','ZAMBIN24']
        if self.africaZscores is None:
            x=ChartEngine(bondlist,ChartTypes.ZScoreVsIndex,'Historical Z-score vs. Africa index',True,10,index='SBAFSOZS')
            self.africaZscores=x.output
        else:
            ChartEngine(bondlist,ChartTypes.ZScoreVsIndex,'Historical Z-score vs. Africa index',True,10,index='SBAFSOZS',source_data=self.africaZscores)
        print self.africaZscores

    def onAfricaWeekly(self,event):
        self.log.Clear()
        self.notebook.SetSelection(0)
        BondTools.africa_weekly()
        pass

    def onCeeWeekly(self,event):
        self.log.Clear()
        self.notebook.SetSelection(0)
        BondTools.cee_weekly()
        pass

    def onCisWeekly(self,event):
        self.log.Clear()
        self.notebook.SetSelection(0)
        BondTools.cis_weekly()
        pass

    def onEurozoneWeekly(self,event):
        self.log.Clear()
        self.notebook.SetSelection(0)
        BondTools.eurozone_weekly()
        pass

    ############MODEL PORTFOLIO ACTIONS############
    def onBuildModelPortfolio(self):
        """Function to build model portfolio
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        busyDlg = wx.BusyInfo('Building model portfolio...', parent=self)
        self.mp=ModelPortfolio.ModelPortfolio()
        self.modelPortfolioLoaded=True
        busyDlg = None

    def onPerformanceChartModelPortfolio(self,event):
        """Function to plot model portfolio performance chart 
        """
        self.log.Clear()
        self.checkModelPortfolio()
        questionlist=['Chart type?','Start year?']
        choiceList=[['Full','Assets','Outperformance'],['2015','2014','2013','2012']]
        data=self.multipleComboQuery(event,'Model portfolio performance chart',questionlist,choiceList)
        year=int(data[1])
        if data[0]=='Full':
            self.mp.plot_full(year,True)
        elif data[0]=='Assets':
            self.mp.plot_assets(year,True)
        else:
            self.mp.plot_outperformance(year,True)

    def onPrintModelPortfolio(self,event):
        """Function to print model portfolio 
        """
        self.log.Clear()
        self.checkModelPortfolio()
        for line in self.mp.display.txtoutput:
            print line

    def onSendModelPortfolioEmail(self,event):
        """Function to send model portfolio to email 
        """
        self.log.Clear()
        self.checkModelPortfolio()
        email = self.textQuery(event,'Email address?','aalmosni2@bloomberg.net')
        self.mp.createoutput(True,email)
        print 'Email sent to '+email
        print ''

    ############FRONT ACTIONS############

    def onLogInFront(self,event=None):
        """Function to log in to FRONT 
        """
        self.log.Clear()
        #Set default username
        self.front_username=traderLogins[GetUserName()]
        dlg = LoginDialog(self.front_username)
        res = dlg.ShowModal()
        editedUser=dlg.user.GetValue()

        #If user changed the value in the dialog, we grab the new value 
        if traderLogins[GetUserName()] != editedUser:
            self.front_username = editedUser
        self.front_password=dlg.password.GetValue()
        dlg.Destroy()
        self.front_connection = FO_Toolkit.FrontConnection(self.front_username, self.front_password)
        self.connectedToFront = True
        pass

    def onTodayTradesSteps(self):
        """Function to load today's trades  
        """
        pythoncom.CoInitialize()
        self.log.Clear()
        if not self.connectedToFront:
            self.onLogInFront()
        savepath = 'newtrades.csv'
        #argstring = self.front_username+' '+self.front_password+' '+self.todayDT.strftime('%Y-%m-%d') + ' ' + savepath
        #opstr='python '+APPPATH+'FO_toolkit.pyc new_trades '+argstring
        #subprocess.call(opstr)
        self.front_connection.new_trades_to_csv(self.todayDT.strftime('%Y-%m-%d'), savepath)
        newTrades = pandas.read_csv(TEMPPATH+savepath)
        self.thToday = TradeHistory(newTrades)
        self.th.appendToday(self.thToday)
        print 'See Trade Activity tab for new trades.'
        pass

    def onTodayTrades(self,event):
        TodayTradesThread(self)
        pass


    def onOpenRepos(self,event):
        """Function to load live repos from FRONT 
        """
        self.log.Clear()
        self.notebook.SetSelection(0)
        if not self.connectedToFront:
            self.onLogInFront(event)
        busyDlg = wx.BusyInfo('Fetching live repos from Front...', parent=self)
        savepath = 'openrepos.csv'
        argstring = self.front_username+' '+self.front_password+' ' + savepath
        opstr='python "'+APPPATH+'FO_toolkit.pyc" open_repos '+argstring#because of the space in global markets
        #print opstr
        subprocess.call(opstr)
        openRepos=pandas.read_csv(TEMPPATH+savepath,index_col=0)
        openRepos['Quantity']=openRepos['Quantity'].apply(lambda y:'{:,.0f}'.format(y))
        busyDlg = None
        print openRepos


    ############ADMINISTRATION ACTIONS############
    def onUpdateBondUniverse(self,event):
        """Function to update bond universe 
        """
        self.log.Clear()
        BondTools.refresh_bond_universe()
        #now need to update all connected stuff

    def onNewClientReport(self,event):
        """Function to create new client report 
        """
        self.log.Clear()
        year=int(self.comboQuery(event,'New client report','Year?',['2016','2015','2014','2013','2012','2011','2010','2009']))
        self.th.newclients(year)

    def onRegs144aReport(self,event):
        """Function to create Regs144a report 
        """
        self.log.Clear()
        self.th.regs144a()

    def onHighSCCheckItem(self,event):
        """Function to print a list of high SC trades 
        """
        self.log.Clear()
        questionlist = ['Year?','Month?','Cutoff SC?']
        choiceList = [['2016','2015','2014','2013','2012','2011','2010','2009'],['Full Year','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],['25','50','100']]
        data = self.multipleComboQuery(event,'SC check',questionlist,choiceList)
        year = int(data[0])
        month = [i for i,x in enumerate(choiceList[1]) if x == data[1]][0]
        limit = int(data[2])
        self.th.highSCCheck(year,month,limit)
        pass

    def onForceRebuildTradeHistory(self, event):
        """Function to force rebuild the trade history 
        """
        TradeHistoryThread(self, True)
        pass

    def onBuildModelPortfolioButton(self, event):
        BuildModelPortfolioThread(self)
        pass

    def onMaDataReportItem(self,event):
        _offsets = (3, 1, 1, 1, 1, 1, 2)
        yesterday = (self.todayDT - datetime.timedelta(days=_offsets[self.todayDT.weekday()])).strftime('%Y%m%d')
        filename=yesterday+'.csv'
        self.log.Clear()
        self.notebook.SetSelection(0)
        x=ma_analysis.MAData(filename)
        x.full_report()
        pass

############MAIN PROGRAM############
# Run the program
if __name__ == "__main__":

    #app = wx.PySimpleApp()
    app = wx.App()
    frame = MainForm().Show()
    app.MainLoop()
