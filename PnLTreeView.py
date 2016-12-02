"""
P&L tree display
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2015 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Classes:

PnLTree

Functions:

tradeVolume()
zeroCondition()
runTest()
"""

import  wx
import  wx.gizmos as gizmos
import pandas
import datetime
from StaticDataImport import ccy as ccy
from StaticDataImport import countries as countries
from StaticDataImport import bonds as bonds
from StaticDataImport import UATPATH


wxVersion=wx.version()[:3]
if wxVersion=='2.8':
    from wx.lib.pubsub import Publisher as pub
else:
    from wx.lib.pubsub import pub



todayDateSTR=datetime.datetime.today().strftime('%d/%m/%y') #Parse today's datetime.datetime into DD/MM/YYYY format

def tradeVolume(th,key,item):
    """Gets the tradeVolume of a bond <= Not used at the moment?? 
    """
    return th.df[(th.df[key]==item) & (th.df['Date']==todayDateSTR)]['Qty'].sum()

def zeroCondition(th,key,item): 
    """Not used at the moment??
    """
    nopos = (th.positions[th.positions[key]==item]['Qty'].min()>=-1 and th.positions[th.positions[key]==item]['Qty'].max()<=1)
    notrades=len(th.df[(th.df[key]==item) & (th.df['Date']==todayDateSTR)])==0
    return (notrades and nopos)


#----------------------------------------------------------------------

class PnLTree(wx.Panel):
    """PnLTree class : Class to define the PnLTree 

    Attributes:
    self.pnlitems : pandas.DataFrame consisting of all PnL items (FrontPnL > DailyPnL.pnlitems)
    self.parent : parent panel (guiWidgets.PnLTabPanel)
    self.tree : wx.Python gizmos.TreeListCtrl object
    
    self.treeKeyDc : Dictionary to contain all the TreeListCtrl wx.Object associated with the bond 
    self.treeCountryDc : Dictionary to contrain all the TreeListCtrl wx.Object associated with the bond's country 
    self.treeIssuerDc : Dictionary to contrain all the TreeListCtrl wx.Object associated with the bond's issuer
    self.treeBookDc : Dictionary to contrain all the TreeListCtrl wx.Object associated with the bond's Book

    
    Methods:
    __init__()
    OnActivate() 
    OnRightUp()
    OnSize()
    onUpdateTree() 
    onRefreshTree()
    """


    def __init__(self, parent, name, pnlitems=[]):
        """
        Keyword arguments:
        parent : parent panel (guiWidgets.PnLTabPanel)
        pnlitems : pandas.DataFrame consisting of all PnL items (FrontPnL > DailyPnL.pnlitems)
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)#-1
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.pnlitems=pnlitems
        self.parent=parent
        self.name = name 

        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)

        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        #smileidx    = il.Add(images.Smiles.GetBitmap())

        self.tree.SetImageList(il)
        self.il = il

        # create some columns
        self.tree.AddColumn("Book / item")  #0
        self.tree.AddColumn("Total USD P&L")#1
        self.tree.AddColumn("SOD pos.")     #2
        self.tree.AddColumn("EOD pos.")     #3
        self.tree.AddColumn("P(yday)")      #4
        self.tree.AddColumn("P(tday)")      #5
        self.tree.AddColumn("SOD P&L")      #6
        self.tree.AddColumn("Trade P&L")    #7
        for i in range(1,8):
            self.tree.SetColumnAlignment(i,wx.ALIGN_RIGHT)
        self.tree.SetMainColumn(0) # self.the one wiself.th self.the tree in it...
        self.tree.SetColumnWidth(0, 175)

        self.root = self.tree.AddRoot("Total")


        self.treeKeyDc={}
        self.treeCountryDc={}
        self.treeIssuerDc={}
        self.treeBookDc={}



        #self.onFillTree()
        self.onUpdateTree()

        self.tree.Expand(self.root)

        self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)

        if self.name == 'live':
            pub.subscribe(self.onRefreshTree, "REFRESH_TREE")
        else:
            pass


    def OnActivate(self, evt):
        """Activates the branch when it's clicked       
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
        else:
            pass

    def OnRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            self.log.write('Flags: %s, Col:%s, Text: %s' %
                           (flags, col, self.tree.GetItemText(item, col)))

    def OnSize(self, evt):
        self.tree.SetSize(self.GetSize())
    



    def onUpdateTreeNew(self, firstBuild=False):
        pythoncom.CoInitialize()
        if firstBuild:
            self.th.positions['EODPrice']=0
            self.th.positions['EODValue']=0
            self.displayPositions=self.th.positions[(self.th.positions['Qty']<=-1) | (self.th.positions['Qty']>=1)].copy()
            self.displayPositions=self.displayPositions.join(bonds['REGS'])
            c=countries.set_index('Country code')
            self.displayPositions=self.displayPositions.join(c['Long name'],on='Country')
            self.displayPositions.rename(columns={'Long name':'LongCountry'},inplace=True)
            displayGroup=self.displayPositions.groupby(['Region','LongCountry','Issuer','Bond']).sum()
            self.doBuildTree(displayGroup,[])
        else:
            wx.CallAfter(self.treeRebuild)

    def treeRebuild(self):
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        pythoncom.CoInitialize()
        _offsets = (3, 1, 1, 1, 1, 1, 2)
        yesterday = (datetime.datetime.today() - datetime.timedelta(days=_offsets[datetime.datetime.today().weekday()])).strftime('%Y-%m-%d')
        c=countries.set_index('Country code')
        traded_bonds = self.th.df[self.th.df['Date']==todayDateSTR]['Bond'].drop_duplicates().dropna().copy()
        new_bonds = list(set(traded_bonds)-set(self.displayPositions.index))
        self.th.positions['EODPrice']=self.EODPrices
        self.th.positions['EODPrice'].fillna(0,inplace=True)
        #print new_bonds
        for bond in new_bonds:
            price = self.fc.historical_price_query(bonds.loc[bond,'REGS'], yesterday)
            if price==0:
                price = self.th.df[self.th.df['Bond']==bond].iloc[-1]['Price']
            self.th.positions.loc[bond,'EODPrice'] = price
        self.EODPrices = self.th.positions['EODPrice'].copy()
        #Retrieve principal factor for traded bonds
        self.th.positions['PRINCIPAL_FACTOR']=self.principalFactor
        if len(new_bonds)>0:
            newisins=map(lambda x:bonds.loc[x,'REGS']+ ' Corp',new_bonds)
            blpts = blpapiwrapper.BLPTS(newisins, ['PRINCIPAL_FACTOR'])
            blpts.get()
            blpts.closeSession()
            blpts.output['REGS'] = blpts.output.index.str[:-5]
            blpts.output['Bond'] = blpts.output['REGS'].replace(isinsregs)
            blpts.output.set_index('Bond', inplace=True)
            self.th.positions.loc[new_bonds,'PRINCIPAL_FACTOR']=blpts.output['PRINCIPAL_FACTOR'].astype(float)
            self.principalFactor=self.th.positions['PRINCIPAL_FACTOR']
        self.th.positions['EODValue']=self.th.positions['EODPrice']*self.th.positions['USDQty']/100.*(self.th.positions['PRINCIPAL_FACTOR'])
        self.displayPositions=self.th.positions.loc[list(self.displayPositions.index)+new_bonds]#SOD risk + new trades
        self.displayPositions=self.displayPositions.join(c['Long name'],on='Country')
        self.displayPositions.rename(columns={'Long name':'LongCountry'},inplace=True)
        displayGroup=self.displayPositions.groupby(['Region','LongCountry','Issuer','Bond']).sum()
        self.doBuildTree(displayGroup,traded_bonds)

    def doBuildTree(self, displayGroup, traded_bonds):
        self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup['Qty'].sum()), 1)
        self.tree.SetItemText(self.root,'{:,.0f}'.format(displayGroup['EODValue'].sum()), 3)
        self.tree.SetItemText(self.root, '{:,.0f}'.format(self.th.df[self.th.df['Date']==todayDateSTR]['Qty'].sum()), 4)#get rid of trades where not a bond
        for region in displayGroup.index.get_level_values('Region').unique():
            childRegion = self.tree.AppendItem(self.root, region)
            self.tree.SetItemImage(childRegion, self.fldridx, which = wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(childRegion, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
            self.treeRegionDc[region]=childRegion
            self.tree.SetItemText(childRegion, '{:,.0f}'.format(displayGroup.loc[region]['Qty'].sum()), 1)
            self.tree.SetItemText(childRegion, '{:,.0f}'.format(displayGroup.loc[region]['EODValue'].sum()), 3)
            self.tree.SetItemText(childRegion,'{:,.0f}'.format(tradeVolume(self.th,'Region',region)), 4)
            for country in displayGroup.loc[region].index.get_level_values('LongCountry').unique():
                childCountry = self.tree.AppendItem(childRegion, country)
                self.tree.SetItemImage(childCountry, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childCountry, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeCountryDc[country] = childCountry
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[region,country]['Qty'].sum()), 1)
                self.tree.SetItemText(childCountry, '{:,.0f}'.format(displayGroup.loc[region,country]['EODValue'].sum()), 3)
                countryCode=countries[countries['Long name']==country]['Country code'].iloc[0]
                self.tree.SetItemText(childCountry,'{:,.0f}'.format(tradeVolume(self.th,'Country',countryCode)), 4)
                for issuer in displayGroup.loc[region,country].index.get_level_values('Issuer').unique():
                    childIssuer = self.tree.AppendItem(childCountry, issuer)
                    self.tree.SetItemImage(childIssuer, self.fldridx, which = wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(childIssuer, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                    self.treeIssuerDc[issuer] = childIssuer
                    self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[region,country,issuer]['Qty'].sum()), 1)
                    self.tree.SetItemText(childIssuer, '{:,.0f}'.format(displayGroup.loc[region,country,issuer]['EODValue'].sum()), 3)
                    self.tree.SetItemText(childIssuer,'{:,.0f}'.format(tradeVolume(self.th,'Issuer',issuer)), 4)
                    for bond in displayGroup.loc[region,country,issuer].index.get_level_values('Bond').unique():
                        childBond = self.tree.AppendItem(childIssuer,  bond)
                        self.tree.SetItemImage(childBond, self.fileidx, which = wx.TreeItemIcon_Normal)
                        self.treeBondDc[bond] = childBond
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['Qty']), 1)
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['USDQty']), 2)
                        self.tree.SetItemText(childBond, '{:,.0f}'.format(displayGroup.loc[region,country,issuer,bond]['EODValue']), 3)
                        self.tree.SetItemText(childBond,'{:,.0f}'.format(tradeVolume(self.th,'Bond',bond)), 4)
                        self.tree.SetItemText(childBond, '{:,.2f}'.format(self.th.positions.loc[bond,'EODPrice']), 5)
                        if bond in list(traded_bonds):#has to be a list
                            self.tree.Expand(childRegion)
        self.tree.Expand(self.root)



    def onUpdateTree(self):
        """Updates the prices displayed by the PnL tree. Function checks if book, country, issuer and key exists in their
        respective dictionaries. If it doesn't, a new child will be created and added to the dictionary.
        """

        for key in self.pnlitems.index:

            book=self.pnlitems.loc[key,'Book']
            country=self.pnlitems.loc[key,'Country']
            issuer=self.pnlitems.loc[key,'Issuer']
            bond = self.pnlitems.loc[key,'Bond']

            #If book is not in self.treeBookDc
            if not book in self.treeBookDc:
                self.treeCountryDc[book]={}#Create an empty nested dictionary in self.treeCountryDc for that book
                self.treeIssuerDc[book]={}#Create an empty nested dictionary in self.IssuerDc for that book

                #Create a childBook item for that book
                childBook = self.tree.AppendItem(self.root, book)
                self.tree.SetItemImage(childBook, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childBook, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeBookDc[book]=childBook#Append the childBook item into self.treeBookDc
            else:
                childBook=self.treeBookDc[book]#If it exists in the dictionary, then load it.

            #If country is not in self.treeCountryDc
            if not country in self.treeCountryDc[book]:
                self.treeIssuerDc[book][country]={}#Create an empty nested dictionary under the 'book' branch 
                                                   #in self.IssuerDc for that country 

                #Create a childCountry item for that book                                    
                childCountry = self.tree.AppendItem(childBook, country)
                self.tree.SetItemImage(childCountry, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childCountry, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeCountryDc[book][country]=childCountry#Append the childCountry item into self.treeCountryDc under the 'book' branch
            else:
                childCountry = self.treeCountryDc[book][country]#If it exist, load the country for that book 

            #If issuer is not in self.treeIssuerDc, create a childIssuer item and add it to the self.treeIssuerDC dict
            #under the branch 'book'>'country'
            if not issuer in self.treeIssuerDc[book][country]:
                childIssuer = self.tree.AppendItem(childCountry, issuer)
                self.tree.SetItemImage(childIssuer, self.fldridx, which = wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(childIssuer, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                self.treeIssuerDc[book][country][issuer]=childIssuer
                #Example:
                #self.treeIssuerDc['APGSG']['Turkey']={'FCFIN':childFCFIN,'TEBNK':childTEBNK}
                #For the Book: APGSG and Country: Turkey, we append Issuer: 'FCFIN' and childIssuer item: 'childFCFIN'
            else:
                childIssuer = self.treeIssuerDc[book][country][issuer]#If it exist, load the issuer for that book                       

            #If the bond doesn't exist in self.treeKeyDc, create a childBond item for that bond.
            #Each 'bond' has a unique 'key'/index in self.pnlitems.index
            if not key in self.treeKeyDc:
                childBond = self.tree.AppendItem(childIssuer, bond)
                self.tree.SetItemImage(childBond, self.fileidx, which = wx.TreeItemIcon_Normal)
                self.treeKeyDc[key]=childBond
            else:
                childBond = self.treeKeyDc[key]#If it exist, load if from the dict

            #Set the item text for the tree items
            self.tree.SetItemText(childBond, '{:,.0f}k'.format(self.pnlitems.loc[key,'SOD_Pos']/1000.), 2)
            self.tree.SetItemText(childBond, '{:,.0f}k'.format(self.pnlitems.loc[key,'EOD_Pos']/1000.), 3)
            self.tree.SetItemText(childBond, '{:,.2f}'.format(self.pnlitems.loc[key,'PriceY']), 4)
            self.tree.SetItemText(childBond, '{:,.2f}'.format(self.pnlitems.loc[key,'PriceT']), 5)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'SOD_PnL']), 6)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'Trade_PnL']), 7)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'USD_Total_PnL']), 1)

            issuertest = self.pnlitems[((self.pnlitems['Issuer']==issuer) & (self.pnlitems['Book']==book))] #Returns boolean series. Selects all bonds under the same book by the same issuer.
            countrytest = self.pnlitems[((self.pnlitems['Country']==country) & (self.pnlitems['Book']==book))] #Returns boolean series. Selects all bonds under the same country by the same issuer.
            
            self.tree.SetItemText(childIssuer, '{:,.0f}'.format(issuertest['USD_Total_PnL'].sum()), 1) #Sums the USD_Total_PnL for that issuer
            self.tree.SetItemText(childCountry, '{:,.0f}'.format(countrytest['USD_Total_PnL'].sum()), 1)#Sums the USD_Total_PnL for that country
            
            self.tree.SetItemText(childBook, '{:,.0f}'.format(self.pnlitems[self.pnlitems['Book']==book]['USD_Total_PnL'].sum()), 1)#Sums the USD_Total_PnL for that book

        self.tree.SetItemText(self.root, '{:,.0f}'.format(self.pnlitems['USD_Total_PnL'].sum()), 1)#Sums all the USD_Total_PnL

        #Sorting
        for book in self.treeBookDc:
            self.tree.SortChildren(self.treeBookDc[book])
            for country in self.treeCountryDc[book]:
                self.tree.SortChildren(self.treeCountryDc[book][country])
                for issuer in self.treeIssuerDc[book][country]:
                    self.tree.SortChildren(self.treeIssuerDc[book][country][issuer])
        
        self.tree.SortChildren(self.root)

        self.tree.SetColumnWidth(1, 100)
        for i in range(2,8):
            self.tree.SetColumnWidth(i, 75)

    def onRefreshTree(self,message):
        """Updates bond analytics when new bond price becomes available.

        Keyword arguments:
        message : message.data returns a pandas.DataFrame consisting of all self.pnlitems items for the bond. 

        E.g     bond    Book   country  issuer  PriceT
            5   AFRLN16 HYCRE  Nigeria  AFRLN   6
            122 AFRLN16 SPOT   Nigeria  AFRLN   6
            123 AFRLN16 SPOT   Nigeria  AFRLN   6

        *Note: A particular bond might belong to different books. There might also more than one items for a same bond 
        under the same book. However each item in the treectrllist is uniquely identified by their pandas.DataFrame index no. 
        E.g. 5, 122 and 123 for the above example.  
        """ 

        data = message.data
        #For each item in the message pandas.DataFrame (e.g. range(3) for the above example)
        for i in range(len(data)):
            #Print Key and Bond to cross check the prices for the item in the tree with the prices menu to verify that
            #all the treelistctrl items for that has indeed been updated. Will be removed once code goes into production.
            print 'Key: ', data.index[i], 'Bond: ',data['Bond'].values[i]

            #Get the key, bond, book, country, issuer for that item
            key = int(data.index[i])
            bond = data['Bond'].values[i]
            book = data['Book'].values[i]
            country = data['Country'].values[i]
            issuer = data['Issuer'].values[i]
            
            #Retrieve the tree child items from the respective dictionaries. These dictionaries were created by 
            #onRefreshTree when the treelistctrl was first created.
            childBond = self.treeKeyDc[key]
            childIssuer=self.treeIssuerDc[book][country][issuer]
            childCountry = self.treeCountryDc[book][country]
            childBook=self.treeBookDc[book]

            #Updates the item text associated with that particular bond.
            self.tree.SetItemText(childBond, '{:,.0f}k'.format(self.pnlitems.loc[key,'SOD_Pos']/1000.), 2)
            self.tree.SetItemText(childBond, '{:,.0f}k'.format(self.pnlitems.loc[key,'EOD_Pos']/1000.), 3)
            self.tree.SetItemText(childBond, '{:,.2f}'.format(self.pnlitems.loc[key,'PriceY']), 4)
            self.tree.SetItemText(childBond, '{:,.2f}'.format(self.pnlitems.loc[key,'PriceT']), 5)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'SOD_PnL']), 6)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'Trade_PnL']), 7)
            self.tree.SetItemText(childBond, '{:,.0f}'.format(self.pnlitems.loc[key,'USD_Total_PnL']), 1)

            issuertest = self.pnlitems[((self.pnlitems['Issuer']==issuer) & (self.pnlitems['Book']==book))] #Returns boolean series. Selects all bonds under the same book by the same issuer.
            countrytest = self.pnlitems[((self.pnlitems['Country']==country) & (self.pnlitems['Book']==book))] #Returns boolean series. Selects all bonds under the same country by the same issuer.
            
            self.tree.SetItemText(childIssuer, '{:,.0f}'.format(issuertest['USD_Total_PnL'].sum()), 1) #Sums the USD_Total_PnL for that issuer
            self.tree.SetItemText(childCountry, '{:,.0f}'.format(countrytest['USD_Total_PnL'].sum()), 1)#Sums the USD_Total_PnL for that country
            
            self.tree.SetItemText(childBook, '{:,.0f}'.format(self.pnlitems[self.pnlitems['Book']==book]['USD_Total_PnL'].sum()), 1)#Sums the USD_Total_PnL for that book

        self.tree.SetItemText(self.root, '{:,.0f}'.format(self.pnlitems['USD_Total_PnL'].sum()), 1)#Sums all the USD_Total_PnL

#----------------------------------------------------------------------

def runTest(frame, nb, log):
    win = TestPanel(nb, log)
    return win

#----------------------------------------------------------------------



overview = """<html><body>
<h2><center>TreeListCtrl</center></h2>

self.the TreeListCtrl is essentially a wx.TreeCtrl wiself.th extra columns,
such self.that the look is similar to a wx.ListCtrl.

</body></html>
"""


if __name__ == '__main__':
    #raw_input("Press enter...")
    #import sys,os
    #import run
    #run.main(['', os.paself.th.basename(sys.argv[0])] + sys.argv[1:])
    app = wx.PySimpleApp()
    frame=wx.Frame(None, wx.ID_ANY, "Flow Trading Tools",size=(825,650))
    win=RiskTree(frame,'hello')
    frame.Show()
    app.MainLoop()

