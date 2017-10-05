"""
Tree display of Front risk
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Functions:
tradeVolume()
zeroCondition()

Class:
RiskTree
"""

import  wx
import  wx.gizmos as gizmos
import pandas
import datetime
import threading
import time
import pythoncom
import win32api
import win32print
import os
from wx import Printout, PrintData, PAPER_LETTER, PrintDialogData
from wx import Printer as wxPrinter, MessageBox, PrintPreview, PrintDialog
from wx.lib.pubsub import pub
from RiskTreeManager import MessageContainer, BondPriceUpdateMessage

import blpapiwrapper
from StaticDataImport import ccy, countries, bonds, BBGHand, TEMPPATH, isinsregs, SPECIALBONDS

todayDateSTR=datetime.datetime.today().strftime('%d/%m/%y')

def tradeVolume(th,key,item):
    return th.df[(th.df[key]==item) & (th.df['Date']==todayDateSTR)]['Qty'].sum()



class MessageContainer():
    def __init__(self,data):
        self.data=data

#def zeroCondition(th,key,item):
#    nopos = (th.positions[th.positions[key]==item]['Qty'].min()>=-1 and th.positions[th.positions[key]==item]['Qty'].max()<=1)
#    notrades=len(th.df[(th.df[key]==item) & (th.df['Date']==todayDateSTR)])==0
#    return (notrades and nopos)


#for testing:
import TradeHistoryAnalysis

#----------------------------------------------------------------------

class RiskTreeOld(wx.Panel):
    """Class to define the Risk Tree Panel 

    Attributes:
    self.treeBondDc : Dictionary to contain childBond (wx.TreeListCtrl object)
    self.treeCountryDc : Dictionary to contain childCountry (wx.TreeListCtrl object)
    self.treeRegionDc : Dictionary to contain childRegion (wx.TreeListCtrl object)
    self.treeIssuerDc : Dictionary to contain childIssuer (wx.TreeListCtrl object)

    Methods:
    __init__()
    OnActivate()
    onCollapseAll()
    onRiskTreeQuery()
    OnRightUp()
    onSize()
    onFillEODPrices()
    onUpdateTree()
    takeScreenshot()

    """
    def __init__(self, parent, riskTreeManager):
        """Keyword arguments:
        parent : parent 
        th = trade history (defaults to empty array if not specified)
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)#-1
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.riskTreeManager = riskTreeManager
        self.parent=parent

        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)

        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        #smileidx    = il.Add(images.Smiles.GetBitmap())

        self.il = il
        self.tree.SetImageList(il)

        # create some columns
        self.tree.AddColumn("Region")#0
        self.tree.AddColumn("Position")#1
        self.tree.AddColumn("USD position")#2
        self.tree.AddColumn("USD PV")#3
        self.tree.AddColumn("SPV01")#4
        self.tree.AddColumn("New trades")#5
        self.tree.AddColumn("Y close")#6
        for i in range(1,7):
            self.tree.SetColumnAlignment(i,wx.ALIGN_RIGHT)
        self.tree.SetMainColumn(0) # self.the one wiself.th self.the tree in it...
        self.tree.SetColumnWidth(0, 175)
        for i in [1,3,4,5,6]:
            self.tree.SetColumnWidth(i,100)
        self.tree.SetColumnWidth(2,0)


        self.root = self.tree.AddRoot("Total")

        self.treeBondDc = {}
        self.treeCountryDc = {}
        self.treeRegionDc = {}
        self.treeIssuerDc = {}

        self.onUpdateTree(MessageContainer('empty'))

        self.tree.Expand(self.root)

        self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
        pub.subscribe(self.onUpdateTree, "REDRAW_RISK_TREE")


    def OnActivate(self, evt):
        """Function to expand tree branch when selected 
        """
        if evt.GetItem() in self.treeBondDc.values():
            self.parent.mainframe.onBondQuerySub(self.tree.GetItemText(evt.GetItem()))
        elif evt.GetItem() in self.treeIssuerDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Issuer',self.tree.GetItemText(evt.GetItem()))
        elif evt.GetItem() in self.treeCountryDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            country_code=countries[countries['Long name']==self.tree.GetItemText(evt.GetItem())]['Country code'].iloc[0]
            self.parent.mainframe.th.simpleQuery('Country',country_code)
        elif evt.GetItem() in self.treeRegionDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Region',self.tree.GetItemText(evt.GetItem()))
        else:
            pass

    def onCollapseAll(self):
        """Function to collapse tree branch when selected 
        """
        for issuer in self.treeIssuerDc:
            self.tree.Collapse(self.treeIssuerDc[issuer])
        for country in self.treeCountryDc:
            self.tree.Collapse(self.treeCountryDc[country])
        for region in self.treeRegionDc:
            self.tree.Collapse(self.treeRegionDc[region])
        pass

    def onRiskTreeQuery(self, item):
        """Function to query risk tree item when selected 
        """
        self.onCollapseAll()
        if item in self.treeIssuerDc:
            exampleBond=bonds[bonds['TICKER']==item].index[0]
            self.tree.Expand(self.treeIssuerDc[item])
            self.tree.Expand(self.treeCountryDc[countries[countries['Country code']==bonds.loc[exampleBond,'CNTRY_OF_RISK']]['Long name'].iloc[0]])
            self.tree.Expand(self.treeRegionDc[countries[countries['Country code']==bonds.loc[exampleBond,'CNTRY_OF_RISK']]['Region'].iloc[0]])            
        elif item in self.treeBondDc:
            self.tree.Expand(self.treeIssuerDc[bonds.loc[item,'TICKER']])
            self.tree.Expand(self.treeCountryDc[countries[countries['Country code']==bonds.loc[item,'CNTRY_OF_RISK']]['Long name'].iloc[0]])
            self.tree.Expand(self.treeRegionDc[countries[countries['Country code']==bonds.loc[item,'CNTRY_OF_RISK']]['Region'].iloc[0]])
        else:
            pass

    def OnRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            x=('Flags: %s, Col:%s, Text: %s' % (flags, col, self.tree.GetItemText(item, col)))
            print x

    def onSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def onUpdateTree(self, message):
        '''Event listener for the REDRAW_RISK_TREE event.
        '''
        wx.CallAfter(self.doBuildTree, self.riskTreeManager.displayGroup,self.riskTreeManager.traded_bonds)

    def doBuildTree(self, displayGroup, traded_bonds):
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup['Qty'].sum()), 1)
        self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup['EODValue'].sum()), 3)
        self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup['Risk'].sum()), 4)
        self.tree.SetItemText(self.root, '{:,.0f}'.format(self.riskTreeManager.th.df[self.riskTreeManager.th.df['Date']==todayDateSTR]['Qty'].sum()), 5)#get rid of trades where not a bond
        for region in displayGroup.index.get_level_values('Region').unique():
            childRegion = self.tree.AppendItem(self.root, region)
            self.tree.SetItemImage(childRegion, self.fldridx, which = wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(childRegion, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
            self.treeRegionDc[region]=childRegion
            self.tree.SetItemText(childRegion, '{:,.0f}'.format(displayGroup.loc[region]['Qty'].sum()), 1)
            self.tree.SetItemText(childRegion, '{:,.0f}'.format(displayGroup.loc[region]['EODValue'].sum()), 3)
            self.tree.SetItemText(childRegion, '{:,.0f}'.format(displayGroup.loc[region]['Risk'].sum()), 4)
            self.tree.SetItemText(childRegion,'{:,.0f}'.format(tradeVolume(self.riskTreeManager.th,'Region',region)), 5)
            for country in displayGroup.loc[region].index.get_level_values('LongCountry').unique():
                childCountry = self.tree.AppendItem(childRegion, country)
                self.tree.SetItemImage(childCountry, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childCountry, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeCountryDc[country] = childCountry
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[region,country]['Qty'].sum()), 1)
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[region,country]['EODValue'].sum()), 3)
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[region,country]['Risk'].sum()), 4)
                countryCode=countries[countries['Long name']==country]['Country code'].iloc[0]
                self.tree.SetItemText(childCountry,'{:,.0f}'.format(tradeVolume(self.riskTreeManager.th,'Country',countryCode)), 5)
                for issuer in displayGroup.loc[region,country].index.get_level_values('Issuer').unique():
                    childIssuer = self.tree.AppendItem(childCountry, issuer)
                    self.tree.SetItemImage(childIssuer, self.fldridx, which = wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(childIssuer, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                    self.treeIssuerDc[issuer] = childIssuer
                    self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[region,country,issuer]['Qty'].sum()), 1)
                    self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[region,country,issuer]['EODValue'].sum()), 3)
                    self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[region,country,issuer]['Risk'].sum()), 4)
                    self.tree.SetItemText(childIssuer,'{:,.0f}'.format(tradeVolume(self.riskTreeManager.th,'Issuer',issuer)), 5)
                    for bond in displayGroup.loc[region,country,issuer].index.get_level_values('Bond').unique():
                        childBond = self.tree.AppendItem(childIssuer,  bond)
                        self.tree.SetItemImage(childBond, self.fileidx, which = wx.TreeItemIcon_Normal)
                        self.treeBondDc[bond] = childBond
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['Qty']), 1)
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['USDQty']), 2)
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['EODValue']), 3)
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['Risk']), 4)
                        self.tree.SetItemText(childBond,'{:,.0f}'.format(tradeVolume(self.riskTreeManager.th,'Bond',bond)), 5)
                        self.tree.SetItemText(childBond, '{:,.2f}'.format(self.riskTreeManager.th.positions.loc[bond,'EODPrice']), 6)
                        if bond in list(traded_bonds):#has to be a list
                            self.tree.Expand(childRegion)
        self.tree.Expand(self.root)
        self.tree.Thaw()
        pub.sendMessage('RISKTREE_REDRAWN', message=MessageContainer('RiskTree'))

    def takeScreenshot(self):
        """
        Function to take screenshot of risk tree. 

        Original code:
        http://www.blog.pythonlibrary.org/2010/04/16/how-to-take-a-screenshot-of-your-wxpython-app-and-print-it/
        """
        print 'Taking screenshot...'
        rect=self.GetRect()
        dcScreen = wx.WindowDC(self)
        bmp = wx.EmptyBitmap(rect.width,rect.height)
        memDC = wx.MemoryDC()

        memDC.SelectObject(bmp)
        memDC.Blit(0,
                   0,
                   rect.width,
                   rect.height,
                   dcScreen,
                   0,
                   0
                   )

        memDC.SelectObject(wx.NullBitmap)

        img = bmp.ConvertToImage()
        filename = 'risktree.png'
        img.SaveFile(filename, wx.BITMAP_TYPE_PNG)
        print '...saving as png...'

        win32api.ShellExecute(0,"print",filename,'/d: "%s"' %win32print.GetDefaultPrinter(), ".",0)

        del dcScreen
        del memDC



class RiskTreeBookPnL(wx.Panel):
    """Class to define the Risk Tree Panel 

    Attributes:
    self.treeBondDc : Dictionary to contain childBond (wx.TreeListCtrl object)
    self.treeCountryDc : Dictionary to contain childCountry (wx.TreeListCtrl object)
    self.treeRegionDc : Dictionary to contain childRegion (wx.TreeListCtrl object)
    self.treeIssuerDc : Dictionary to contain childIssuer (wx.TreeListCtrl object)

    Methods:
    __init__()
    OnActivate()
    onCollapseAll()
    onRiskTreeQuery()
    OnRightUp()
    onSize()
    onFillEODPrices()
    onUpdateTree()
    takeScreenshot()

    """
    def __init__(self, parent, riskTreeManager):
        """Keyword arguments:
        parent : parent 
        th = trade history (defaults to empty array if not specified)
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)#-1
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.riskTreeManager = riskTreeManager
        self.parent=parent
        self.LivePricesFilled=False

        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)

        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        #smileidx    = il.Add(images.Smiles.GetBitmap())

        self.il = il
        self.tree.SetImageList(il)

        # create some columns
        self.tree.AddColumn("Book")#0
        self.tree.AddColumn("Position")#1
        self.tree.AddColumn("USD PV")#2
        self.tree.AddColumn("SPV01")#3
        self.tree.AddColumn("Total USD P&L")#4
        self.tree.AddColumn("Mark-up")#5
        #Separator
        self.tree.AddColumn("SOD pos.")     #6
        self.tree.AddColumn("P(T-1)")      #7
        self.tree.AddColumn("P(T)")      #8
        self.tree.AddColumn("SOD P&L")      #9
        self.tree.AddColumn("Trade P&L")    #10

        for i in range(1,11):
            self.tree.SetColumnAlignment(i,wx.ALIGN_RIGHT)
        self.tree.SetMainColumn(0)
        self.tree.SetColumnWidth(0, 175)
        for i in range(1,11):
            self.tree.SetColumnWidth(i,100)
        self.tree.SetColumnWidth(7,50)
        self.tree.SetColumnWidth(8,50)


        self.root = self.tree.AddRoot("Total")

        #self.treeIsinDc = {}
        self.treeBondDc = {}
        self.treeIssuerDc = {}
        self.treeCountryDc = {}
        self.treeBookDc = {}
        self.treeSeriesDc = {}

        self.onUpdateTree(MessageContainer('empty'))
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)

        self.tree.Expand(self.root)
        pub.subscribe(self.onUpdateTree, "REDRAW_TREE")
        pub.subscribe(self.onUpdatePrice, "RISKTREE_BOND_PRICE_UPDATE")

        #self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        #self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)


    def onUpdatePrice(self, message):
        '''Event listener for the RISKTREE_BOND_PRICE_UPDATE event.
        '''
        wx.CallAfter(self.doUpdatePrice, message)

    def doUpdatePrice(self, message):
        #at this point - I know that the bond IS in the tree, and I know which books - so just looping on series
        colIDs = [4,9,10]
        colNames = ['TotalPnL','SODPnL','TradePnL']
        zipped = zip(colIDs,colNames)

        bond = message.bond
        #country = self.riskTreeManager.cntrymap.at[bonds.at[bond,'CNTRY_OF_RISK'],'Long name']
        country = self.riskTreeManager.cntrymap.at[bonds.at[bond,'CNTRY_OF_RISK'],'LongCountry']#we have renamed Long name to LongCountry in the riskTreeManager
        issuer = bonds.at[bond,'TICKER']
        booklist = message.booklist
        isins = [bonds.at[bond,'REGS'],bonds.at[bond,'144A']]
        df = self.riskTreeManager.th.positionsByISINBook
        
        for (i,col) in zipped:
            self.tree.SetItemText(self.root, '{:,.0f}'.format(df[col].sum()), i)
        
        for book in booklist:

            for series in ['REGS','144A']:
                key = (book, country, issuer, bond, series)
                if key in self.treeSeriesDc:#144A MIGHT NOT BE THERE FOR INSTANCE
                    childSeries = self.treeSeriesDc[key]
                    self.tree.SetItemText(childSeries, '{:,.2f}'.format(message.price), 8)
                    for (i,col) in zipped:
                        self.tree.SetItemText(childSeries, '{:,.0f}'.format(df.at[book+'-'+bonds.at[bond,series],col]), i)
            
            childBond = self.treeBondDc[(book, country, issuer, bond)]
            view=df.loc[(df['Book']==book) & (df['Bond']==bond)]
            for (i,col) in zipped:
                self.tree.SetItemText(childBond, '{:,.0f}'.format(view[col].sum()), i)
            
            childIssuer = self.treeIssuerDc[(book, country, issuer)]
            view=df.loc[(df['Book']==book) & (df['Issuer']==issuer)]
            for (i,col) in zipped:
                self.tree.SetItemText(childIssuer, '{:,.0f}'.format(view[col].sum()), i)
            
            childCountry = self.treeCountryDc[(book, country)]
            view=df.loc[(df['Book']==book) & (df['LongCountry']==country)]
            for (i,col) in zipped:
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(view[col].sum()), i)
            
            childBook = self.treeBookDc[book]
            view=df.loc[(df['Book']==book)]
            for (i,col) in zipped:
                self.tree.SetItemText(childBook, '{:,.0f}'.format(view[col].sum()), i)



    def OnActivate(self, evt):
        """Function to expand tree branch when selected 
        """
        if evt.GetItem() in self.treeBondDc.values():
            self.parent.mainframe.onBondQuerySub(self.tree.GetItemText(evt.GetItem()))
        elif evt.GetItem() in self.treeIssuerDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Issuer',self.tree.GetItemText(evt.GetItem()))
        elif evt.GetItem() in self.treeCountryDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            country_code=countries[countries['Long name']==self.tree.GetItemText(evt.GetItem())]['Country code'].iloc[0]
            self.parent.mainframe.th.simpleQuery('Country',country_code)
        elif evt.GetItem() in self.treeBookDc.values():
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Book',self.tree.GetItemText(evt.GetItem()))
        else:
            pass

    def onSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def onUpdateTree(self, message):
        '''Event listener for the REDRAW_RISK_TREE event.
        '''
        wx.CallAfter(self.doBuildTree, self.riskTreeManager.displayGroupBook,self.riskTreeManager.traded_bonds)


    def doBuildTree(self, displayGroup, traded_bonds):
        #WARNING: SODPNL SUMS CONFUSES CURRENCIES
        colIDs = [1,2,3,4,5,6,9,10]
        colNames = ['Qty','EODValue','Risk','TotalPnL','MK','SOD_Pos','SODPnL','TradePnL']
        zipped = zip(colIDs,colNames)
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        for (i,col) in zipped:
            self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup[col].sum()), i)
        
        for book in displayGroup.index.get_level_values('Book').unique():
            childBook = self.tree.AppendItem(self.root, book)
            self.tree.SetItemImage(childBook, self.fldridx, which = wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(childBook, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
            self.treeBookDc[book]=childBook
            for (i,col) in zipped:
                self.tree.SetItemText(childBook, '{:,.0f}'.format(displayGroup.loc[book][col].sum()), i)
        
            for country in displayGroup.loc[book].index.get_level_values('LongCountry').unique():
                childCountry = self.tree.AppendItem(childBook, country)
                self.tree.SetItemImage(childCountry, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childCountry, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeCountryDc[(book, country)] = childCountry
                for (i,col) in zipped:
                    self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[book,country][col].sum()), i)
        
                for issuer in displayGroup.loc[book,country].index.get_level_values('Issuer').unique():
                    childIssuer = self.tree.AppendItem(childCountry, issuer)
                    self.tree.SetItemImage(childIssuer, self.fldridx, which = wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(childIssuer, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                    self.treeIssuerDc[(book, country, issuer)] = childIssuer
                    for (i,col) in zipped:
                        self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[book,country,issuer][col].sum()), i)
        
                    for bond in displayGroup.loc[book,country,issuer].index.get_level_values('Bond').unique():
                        childBond = self.tree.AppendItem(childIssuer,  bond)
                        self.tree.SetItemImage(childBond, self.fileidx, which = wx.TreeItemIcon_Normal)
                        self.tree.SetItemImage(childBond, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                        self.treeBondDc[(book, country, issuer, bond)] = childBond
                        for (i,col) in zipped:
                            self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[book,country,issuer,bond][col].sum()), i)
        
                        for series in displayGroup.loc[book,country,issuer,bond].index.get_level_values('Series').unique():
                            childSeries = self.tree.AppendItem(childBond,  series)
                            self.tree.SetItemImage(childSeries, self.fileidx, which = wx.TreeItemIcon_Normal)
                            self.treeSeriesDc[(book, country, issuer, bond, series)] = childSeries
                            self.tree.SetItemText(childSeries, '{:,.2f}'.format(displayGroup.loc[book,country,issuer,bond,series]['PriceY']), 7)
                            self.tree.SetItemText(childSeries, '{:,.2f}'.format(displayGroup.loc[book,country,issuer,bond,series]['PriceT']), 8)
                            for (i,col) in zipped:
                                self.tree.SetItemText(childSeries, '{:,.0f}'.format(displayGroup.loc[book,country,issuer,bond,series][col]), i)
        
        self.tree.Expand(self.root)
        pub.sendMessage('TREE_REDRAWN', message=MessageContainer('BOOK_RISK_TREE'))
        #print self.treeSeriesDc


class DataFrameToTreeListCtrl(wx.Panel):
    """
    """
    def __init__(self, parent, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, strTreeID):
        """Keyword arguments:
        parent : parent 
        th = trade history (defaults to empty array if not specified)
        #groupedData in a multiindex Dataframe, typically the result of a df.groupby[columnList].sum()
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)#-1
        self.parent=parent
        self.df = df
        self.groupList = groupList
        self.treeHeader = treeHeader
        self.treeHeaderWidth = treeHeaderWidth
        self.columnHeaders = columnHeaders
        self.columnList = columnList
        self.columnWidths = columnWidths
        self.columnAlignment = columnAlignment
        self.columnFormats = columnFormats
        self.strTreeID = strTreeID
        #self.groupedData = df.groupby(self.groupList)
        #self.groupedDataSum = self.groupedData[columnList].sum()
        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)
        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self.il = il
        self.tree.SetImageList(il)
        # create some columns
        self.tree.AddColumn(self.treeHeader)
        self.tree.SetColumnAlignment(0,wx.ALIGN_LEFT)
        self.tree.SetColumnWidth(0,self.treeHeaderWidth)
        for i, (c,w,a) in enumerate(zip(columnHeaders,columnWidths,columnAlignment)):
            self.tree.AddColumn(c)
            self.tree.SetColumnAlignment(i+1,a)
            self.tree.SetColumnWidth(i+1,w)
        self.tree.SetMainColumn(0)
        #Bind events
        self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onActivate)
        pub.subscribe(self.onUpdateTree, "REDRAW_TREE")
        #First draw
        self.onUpdateTree(MessageContainer('empty'))

    def onActivate(self,evt):
        self.active_path = []
        item = self.tree.GetSelection()
        while self.tree.GetItemParent(item):
            label = self.tree.GetItemText(item)
            self.active_path.insert(0, label)
            item = self.tree.GetItemParent(item)
        print self.active_path

    def onCollapseAll(self):
        self.recursiveCollapse(self.tree.GetRootItem())

    def recursiveCollapse(self, item):
        self.tree.Collapse(item)
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            self.recursiveCollapse(child)
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onQuery(self, itemText):
        self.search_path_list = []
        self.recursiveSearch(self.tree.GetRootItem(), itemText, [])
        pass

    def recursiveSearch(self, item, itemText, path_to_here):
        text = self.tree.GetItemText(item)
        res = list(path_to_here)
        res.append(text)
        if text == itemText:
            self.search_path_list.append(res)
        else:
            (child, cookie) = self.tree.GetFirstChild(item)
            while child.IsOk():
                self.recursiveSearch(child,itemText,res)
                (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onExpand(self, pathList):
        for p in pathList:
            self.recursiveExpand(self.tree.GetRootItem(),p)

    def recursiveExpand(self, item, remaining_path):
        text = self.tree.GetItemText(item)
        if text == remaining_path[0]:
            self.tree.Expand(item)
            if len(remaining_path)>1:
                (child, cookie) = self.tree.GetFirstChild(item)
                while child.IsOk():
                    self.recursiveExpand(child,remaining_path[1:])
                    (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            x=('Flags: %s, Col:%s, Text: %s' % (flags, col, self.tree.GetItemText(item, col)))
            print x

    def onSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def onUpdateTree(self, message):
        '''Event listener for the REDRAW_RISK_TREE event.
        '''
        self.groupedData = self.df.groupby(self.groupList)
        self.groupedDataSum = self.groupedData[self.columnList].sum()
        wx.CallAfter(self.drawTree)

    def drawLeaf(self, lvl, parent, parentItemList):
        if lvl == 0:
            generator = self.groupedDataSum.index.get_level_values(0).unique()
        else:
            generator = self.groupedDataSum.loc[tuple(parentItemList)].index.get_level_values(0).unique()
        for item in generator:
                child = self.tree.AppendItem(parent,item)
                itemList = list(parentItemList)
                itemList.append(item)
                if lvl < self.groupedDataSum.index.nlevels - 1:
                    self.tree.SetItemImage(child, self.fldridx, which = wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(child, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                else:
                    self.tree.SetItemImage(child, self.fileidx, which = wx.TreeItemIcon_Normal)
                for i, (c,f) in enumerate(zip(self.columnList,self.columnFormats)):
                    self.tree.SetItemText(child, f.format(self.groupedDataSum.loc[tuple(itemList)][c].sum()), i+1)
                if lvl < self.groupedDataSum.index.nlevels - 1:
                    self.drawLeaf(lvl+1, child, itemList)

    def drawTree(self):
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        for i,(c,f) in enumerate(zip(self.columnList,self.columnFormats)):
            self.tree.SetItemText(self.root, f.format(self.groupedDataSum[c].sum()), i+1)
        self.drawLeaf(0,self.root,[])
        self.tree.Expand(self.root)
        self.tree.Thaw()
        pub.sendMessage('TREE_REDRAWN', message=MessageContainer(self.strTreeID))
        #self.onCollapseAll()


class TreeTest(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None, wx.ID_ANY, "Tree test",size=(925,850))
        #panel = wx.Panel(frame)
        #th = TradeHistoryAnalysis.TradeHistory()
        #df = th.df[th.df['Year']==2016]
        #df.to_csv('c:\\temp\\treetest.csv')
        df = pandas.read_csv('c:\\temp\\treetest.csv')
        groupedData = df.groupby(['Region','Country','Bond'])
        treeHeader = 'Region'
        treeHeaderWidth = 200
        columnHeaders = ['Position','Volume']
        columnList = ['USDQty','AbsQty']
        columnWidths = [100,200]
        columnAlignment = [wx.ALIGN_RIGHT,wx.ALIGN_RIGHT]
        columnFormats = ['{:,.0f}','{:,.0f}']
        tree = DataFrameToTreeListCtrl(self, groupedData, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, 'TEST_TREE')
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(tree, 1, wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Layout()


class RiskTree(DataFrameToTreeListCtrl):
    def __init__(self, parent, riskTreeManager):
        self.riskTreeManager = riskTreeManager
        groupList =  ['Region','LongCountry','Issuer','Bond']
        treeHeader = 'Region'
        treeHeaderWidth = 175
        columnHeaders = ['Position', 'Gross USD PV', 'Net USD PV', 'SPV01','New Trades']#, 'New Trades','Y close']
        columnList = ['Qty', 'GrossUSDPV', 'EODValue','Risk','NewTrades']#,'Volume','EODPrice']
        columnWidths = [100,100,100,100,100]
        columnAlignment = [wx.ALIGN_RIGHT,wx.ALIGN_RIGHT,wx.ALIGN_RIGHT,wx.ALIGN_RIGHT,wx.ALIGN_RIGHT]
        columnFormats = ['{:,.0f}','{:,.0f}','{:,.0f}','{:,.0f}','{:,.0f}']
        DataFrameToTreeListCtrl.__init__(self, parent, self.riskTreeManager.th.positionsByISINBook, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, 'MAIN_RISK_TREE')

    def onUpdateTree(self,message):
        self.df = self.riskTreeManager.th.positionsByISINBook
        self.df['GrossUSDPV'] = self.df['EODValue'].abs()
        #self.df.to_csv(TEMPPATH+'testrisktree.csv')
        super(RiskTree,self).onUpdateTree(message)

    def onActivate(self, evt):
        super(RiskTree,self).onActivate(evt)
        lap = len(self.active_path)
        if lap==4:
            self.parent.mainframe.onBondQuerySub(self.active_path[lap-1])
        elif lap==3:
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Issuer',self.active_path[lap-1])
        elif lap==2:
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            country_code=countries[countries['Long name']==self.active_path[lap-1]]['Country code'].iloc[0]
            self.parent.mainframe.th.simpleQuery('Country',country_code)
        elif lap==1:
            self.parent.mainframe.log.Clear()
            self.parent.mainframe.notebook.SetSelection(0)
            self.parent.mainframe.th.simpleQuery('Region',self.active_path[lap-1])
        else:
            pass

    def onRiskTreeQuery(self, itemText):
        self.onQuery(itemText)
        self.onCollapseAll()
        self.onExpand(self.search_path_list)


class IRRiskTree(DataFrameToTreeListCtrl):
    def __init__(self, parent, riskTreeManager):
        self.riskTreeManager = riskTreeManager
        groupList = ['CCY','Book']
        treeHeader = 'Group'
        treeHeaderWidth = 150
        columnHeaders = ['Sum','<6M', '1Y', '2Y','3Y','4Y','5Y','6Y','7Y','8Y','9Y','10Y', '12Y', '15Y','20Y','25Y','30Y', '>32.5Y']#, 'New Trades','Y close']
        self.bins = pandas.np.array([0,0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,11,13.5,17.5,22.5,27.5,35,1000])
        # data = self.riskTreeManager.th.positionsByISINBook
        # data['bins'] = pandas.cut(data['SAVG'],self.bins)
        # data = data.groupby(['CCY','Book','bins'])['Risk'].sum()
        # data = data.unstack()
        # data.fillna(0,inplace=True)
        # data.columns = data.columns.astype(str)
        # data.reset_index(inplace=True)
        columnList = [u'Sum', u'(0, 0.5]', u'(0.5, 1.5]', u'(1.5, 2.5]', u'(2.5, 3.5]', u'(3.5, 4.5]', u'(4.5, 5.5]', u'(5.5, 6.5]', u'(6.5, 7.5]', u'(7.5, 8.5]', u'(8.5, 9.5]', u'(9.5, 11.0]', u'(11.0, 13.5]', u'(13.5, 17.5]', u'(17.5, 22.5]', u'(22.5, 27.5]', u'(27.5, 35.0]', u'(35.0, 1000.0]']
        # for c in columnList:
        #     if c not in data:
        #         data[c] = 0.0
        # data['Sum'] = data[columnList[1:]].sum(axis=1)
        #print data.columns
        #print columnList
        columnWidths = [50 for i in range(len(self.bins)-1)]
        columnAlignment = [wx.ALIGN_RIGHT for i in range(len(self.bins)-1)]
        columnFormats = ['{:,.0f}' for i in range(len(self.bins)-1)]
        DataFrameToTreeListCtrl.__init__(self, parent, self.riskTreeManager.th.positionsByISINBook, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, 'IR_RISK_TREE')

    def onUpdateTree(self,message):
        data = self.riskTreeManager.th.positionsByISINBook
        data['bins'] = pandas.cut(data['SAVG'],self.bins)
        data = data.groupby(['CCY','Book','bins'])['IRRisk'].sum()
        data = data.unstack()
        data.fillna(0,inplace=True)
        data.columns = data.columns.astype(str)
        data.reset_index(inplace=True)
        for c in self.columnList:
            if c not in data:
                data[c] = 0.0
        data['Sum'] = data[self.columnList[1:]].sum(axis=1)
        self.df = data
        super(IRRiskTree,self).onUpdateTree(message)



if __name__ == "__main__":
    app = wx.App()
    frame = TreeTest().Show()
    app.MainLoop()
