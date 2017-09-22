"""
GUI widgets feeding FlowTradingGUI.py
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

"""

import wx
import datetime
import wx.grid as gridlib
import wx.lib.colourdb
from wx.lib.pubsub import pub

from RiskTreeView import RiskTree, RiskTreeBookPnL, IRRiskTree
from PnLTreeView import PnLTree
import datetime
import FO_Toolkit



class GenericRiskTabPanel(wx.Panel):

    def __init__(self, txtID, designClass, riskTreeManager, parentnotebook, mainframe):
        """
        Keyword argument:
        tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory
        parentnotebook : wx.Python notebook object
        mainframe : wx.Python frame object
        """
        self.txtID = txtID
        self.riskTreeManager = riskTreeManager
        self.parentnotebook = parentnotebook
        self.mainframe = mainframe
        self.designClass = designClass
        pub.subscribe(self.updatePositions, 'TREE_REDRAWN')
        wx.Panel.__init__(self, parent=parentnotebook)
        self.drawPanel()

    def lastUpdateString(self):
        if self.riskTreeManager.th.df['Date'].iloc[-1]!=datetime.datetime.today().strftime('%d/%m/%y'):
            return 'Last updated on ' + self.riskTreeManager.th.df['Date'].iloc[-1] + '.'
        else:
            return 'Last updated today at ' + datetime.datetime.now().strftime('%H:%M') + '.'

    def drawPanel(self):
        """Draws the Risk panel 
        """
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn = wx.Button(self, label="Refresh Front data")
        self.btn.Bind(wx.EVT_BUTTON, self.onRefreshFrontData)
        btn3 = wx.Button(self, label = "Print risk tree")
        btn3.Bind(wx.EVT_BUTTON, self.onPrintRiskTree) 
        self.sizer1.Add(self.btn, 1, wx.ALL, 2)
        self.sizer1.Add(btn3, 0.5, wx.ALL, 2)
        self.lastUpdateTime = wx.TextCtrl(self,-1,self.lastUpdateString())
        self.sizer2.Add(self.lastUpdateTime,1,wx.ALL,2)
        self.riskTree = self.designClass(self,self.riskTreeManager)
        self.sizerRiskH = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerRiskH.Add(self.riskTree,proportion=1,flag=wx.EXPAND)
        self.sizerRiskV = wx.BoxSizer(wx.VERTICAL)
        self.sizerRiskV.Add(self.sizerRiskH,proportion=1,flag=wx.EXPAND)
        self.topSizer.Add(self.sizer1, 0, wx.ALL|wx.EXPAND, 2)
        self.topSizer.Add(self.sizer2, 0, wx.ALL|wx.EXPAND, 2)
        self.topSizer.Add(self.sizerRiskV, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(self.topSizer)
        self.Layout()
        pass

    def onRefreshFrontData(self,event):
        """Refreshes Front data. Function is called when the 'Refresh Front data' button is clicked.
        """
        self.btn.Disable()
        if not self.riskTreeManager.EODPricesFilled:
            self.onFillEODPrices(event)
        self.lastUpdateTime.SetValue('Requested data update, please wait...')
        self.mainframe.onTodayTrades(event)
        pass


    def updatePositions(self,message=None):
        """event listener for the POSITION_UPDATE event. Updates position when the event is publicised 
        """
        #self.riskTreeManager.onUpdateTree()
        #self.parentnotebook.SetSelection(1)
        if message.data == self.txtID:
            self.lastUpdateTime.SetValue(self.lastUpdateString())
            self.btn.Enable()
        pass

    def onFillEODPrices(self,event):
        """Function is called when the 'Fill USD PV' button is clicked.
        """
        #self.btn2.Disable()
        x=self.lastUpdateTime.GetValue()
        self.lastUpdateTime.SetValue('Refreshing EOD prices from Front...')
        if not self.mainframe.connectedToFront:
            self.mainframe.onLogInFront(event)
            #fc = FO_Toolkit.FrontConnection(self.mainframe.front_username,self.mainframe.front_password)
        if not self.riskTreeManager.EODPricesFilled:
            #self.riskTreeManager.onFillEODPrices(fc)
            self.riskTreeManager.onFillEODPrices(self.mainframe.front_connection)
        self.lastUpdateTime.SetValue(x)
        pass

    def onPrintRiskTree(self, event):
        """Function to call RiskTreeView.takeScreenshot() to take a screenshot of the risk tree.
        """
        self.riskTree.takeScreenshot()

    def onRiskTreeQuery(self, event, item):
        """Calls the RiskTreeView > RiskTree.onRiskTreeQuery function  
        """
        self.riskTree.onRiskTreeQuery(item)
        pass
    pass


class RiskTabPanel(GenericRiskTabPanel):
    def __init__(self, riskTreeManager, parentnotebook, mainframe):
        GenericRiskTabPanel.__init__(self, 'MAIN_RISK_TREE', RiskTree, riskTreeManager, parentnotebook, mainframe)
        pass


class IRRiskTabPanel(GenericRiskTabPanel):
    def __init__(self, riskTreeManager, parentnotebook, mainframe):
        GenericRiskTabPanel.__init__(self, 'IR_RISK_TREE', IRRiskTree, riskTreeManager, parentnotebook, mainframe)
        pass


class BookRiskPnLTabPanel(GenericRiskTabPanel):
    def __init__(self, riskTreeManager, parentnotebook, mainframe):
        GenericRiskTabPanel.__init__(self, 'BOOK_RISK_TREE', RiskTreeBookPnL, riskTreeManager, parentnotebook, mainframe)
        pass


class LoginDialog(wx.Dialog):
    """Class to define the login dialog. Function is used in FlowTradingGUI
    """
    #----------------------------------------------------------------------
    def __init__(self,username):
        """Constructor

        Function automatically fills the username field with the user's Front Login ID.
        Both username and password are editable fields.
        """
        self.username = username
        wx.Dialog.__init__(self, None, title="Front login")
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        fgs = wx.FlexGridSizer(3, 2, 9, 25)        
        user_lbl = wx.StaticText(self, label="User name:")
        self.user = wx.TextCtrl(self)
        self.user.SetValue(str(self.username))
        p_lbl = wx.StaticText(self, label="Password:")
        self.password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        fgs.AddMany([(user_lbl), (self.user, 1, wx.EXPAND), (p_lbl), (self.password, 1, wx.EXPAND)])
        fgs.AddGrowableRow(2, 1)
        fgs.AddGrowableCol(1, 1)
        hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        okBtn = wx.Button(self, wx.ID_OK)
        vbox.Add(hbox,0,wx.ALL|wx.CENTER, 5)
        vbox.Add(okBtn,0,wx.ALL|wx.CENTER, 5)
        self.password.SetFocus()
        self.SetSizer(vbox)
        self.SetSizerAndFit(vbox)        
        self.Centre()

class PromptingComboBox(wx.ComboBox) :
    """PromptingComboBox class: Class to define the wx.ComboBox object. 
    Class is used by the query and combo dialogs.

    Attributes:

    Methods:
    __init__()
    EvtCombobox()
    EvtChar()
    EvtText()
    """
    def __init__(self, parent, value, choices=[], style=0, **par):
        """Keyword arguments:

        parent:
        value: Choice 
        choices: List of choices (array). Defaults to an empty array if not specified
        style: Defaults to 0
        """
        wx.ComboBox.__init__(self, parent, wx.ID_ANY, value, style=style|wx.CB_DROPDOWN, choices=choices, **par)
        self.choices = choices
        self.Bind(wx.EVT_TEXT, self.EvtText)
        self.Bind(wx.EVT_CHAR, self.EvtChar)
        self.Bind(wx.EVT_COMBOBOX, self.EvtCombobox)
        self.ignoreEvtText = False

    def EvtCombobox(self, event):
        self.ignoreEvtText = True
        event.Skip()

    def EvtChar(self, event):
        if event.GetKeyCode() == 8:
            self.ignoreEvtText = True
        event.Skip()

    def EvtText(self, event):
        if self.ignoreEvtText:
            self.ignoreEvtText = False
            return
        currentText = event.GetString()
        found = False
        for choice in self.choices :
            if choice.startswith(currentText):
                #self.ignoreEvtText = True  AA CHANGE 28OCT14
                self.SetValue(choice)
                self.SetInsertionPoint(len(currentText))
                self.SetMark(len(currentText), len(choice))
                found = True
                break
        if not found:
            event.Skip()

class ComboDialog(wx.Dialog):
    """ComboDialog Class : Class to define the combo dialog. Class is used in FlowTradinGUI.py
    """
    def __init__(self,myTitle,question,myChoices):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=myTitle)
        self.toLbl = wx.StaticText(self, label=question)
        self.comboBox1 = PromptingComboBox(self,myChoices[0],myChoices)
        okBtn = wx.Button(self, wx.ID_OK)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.toLbl, 0, wx.ALL|wx.CENTER, 5)
        sizer.Add(self.comboBox1, 0, wx.ALL|wx.CENTER, 5)
        sizer.Add(okBtn, 0, wx.ALL|wx.CENTER, 5)
        self.SetSizer(sizer)
        self.SetAutoLayout(1)
        sizer.Fit(self)

class MultipleComboDialog(wx.Dialog):
    """MultipleComboDialog Class: Class to define to multiple combo dialog. Class is used in FlowTradingGUI.py
    """
    def __init__(self,myTitle,myQuestionList,myChoicesList):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=myTitle)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.comboBoxList=[]
        self.sizerList=[]
        for myQuestion,myChoice in zip(myQuestionList,myChoicesList):
            s=wx.BoxSizer(wx.HORIZONTAL)
            q=wx.StaticText(self, label=myQuestion)
            x=PromptingComboBox(self,myChoice[0],myChoice)
            self.comboBoxList.append(x)
            s.Add(q, 0, wx.ALL|wx.CENTER, 5)
            s.Add(x, 0, wx.ALL|wx.CENTER, 5)
            self.sizerList.append(s)
            self.mainSizer.Add(s, 0, wx.ALL|wx.CENTER, 5)
        okBtn = wx.Button(self, wx.ID_OK)
        self.mainSizer.Add(okBtn, 0, wx.ALL|wx.CENTER, 5)
        self.SetSizer(self.mainSizer)
        self.SetAutoLayout(1)
        self.mainSizer.Fit(self)

class AdvancedQuery(wx.Dialog):
    """Class to define the AdvancedQuery dialog box. Class is called when the 'Advanced Query' item in the 'Trade History'
    menu is selected.

    Methods:

    __init__()
    editComboBox2()
    """
    def __init__(self, parent, mytitle):
        """Keyword arguments:
        parent : mainframe 
        mytitle : title of dialog box 
        """
        wx.Dialog.__init__(self, parent, wx.ID_ANY, mytitle)
        self.parent=parent
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        fgs = wx.FlexGridSizer(0, 0, 9, 25)#3,2  => 0,0 means it grows dynamically
        self.queryTypeLabel = wx.StaticText(self, label='Query type?')
        myChoices=['Bond','Client','Salesperson','Issuer','Country']
        self.queryType=myChoices[0]
        #self.comboBox1 = PromptingComboBox(self,myChoices[0],myChoices)
        self.comboBox1=wx.ComboBox(self, wx.ID_ANY, myChoices[0], style=wx.CB_DROPDOWN, choices=myChoices)
        sizerQueryType = wx.BoxSizer(wx.HORIZONTAL)
        sizerQueryType.Add(self.queryTypeLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerQueryType.Add(self.comboBox1, 0, wx.ALL|wx.CENTER, 5)
        self.queryIDLabel = wx.StaticText(self, label='ID?')
        myChoices=parent.bondlist
        self.comboBox2 = PromptingComboBox(self,myChoices[0],myChoices)
        self.Bind(wx.EVT_COMBOBOX, self.editComboBox2,self.comboBox1)
        #self.Bind(wx.EVT_TXT, self.editComboBox2,self.comboBox1)
        sizerQueryID = wx.BoxSizer(wx.HORIZONTAL)
        sizerQueryID.Add(self.queryIDLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerQueryID.Add(self.comboBox2, 0, wx.ALL|wx.CENTER, 5)
        self.startDateLabel = wx.StaticText(self, label='Start date?')
        self.startcalendar = wx.DatePickerCtrl(self, wx.ID_ANY, wx.DateTime_Now())
        sizerStartDate = wx.BoxSizer(wx.HORIZONTAL)
        sizerStartDate.Add(self.startDateLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerStartDate.Add(self.startcalendar, 0, wx.ALIGN_RIGHT|wx.CENTER, 5)
        self.endDateLabel = wx.StaticText(self, label='End date?')
        self.endcalendar = wx.DatePickerCtrl(self, wx.ID_ANY, wx.DateTime_Now())
        sizerEndDate = wx.BoxSizer(wx.HORIZONTAL)
        sizerEndDate.Add(self.endDateLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerEndDate.Add(self.endcalendar, 0, wx.ALIGN_RIGHT|wx.CENTER, 5)
        fgs.AddMany([(self.queryTypeLabel), (self.comboBox1, 1, wx.EXPAND), (self.queryIDLabel), (self.comboBox2, 1, wx.EXPAND), (self.startDateLabel, 1, wx.EXPAND), (self.startcalendar, 1, wx.EXPAND),(self.endDateLabel, 1, wx.EXPAND), (self.endcalendar, 1, wx.EXPAND)])
        #fgs.AddGrowableRow(2, 1)
        #fgs.AddGrowableCol(1, 1)
        hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        okBtn = wx.Button(self, wx.ID_OK)
        vbox.Add(hbox,0,wx.ALL|wx.CENTER, 5)
        vbox.Add(okBtn,0,wx.ALL|wx.CENTER, 5)
        self.SetSizer(vbox)
        self.SetSizerAndFit(vbox)        
        self.Centre()

    def editComboBox2(self,event):
        """Function is called when an item in the combobox is selected. 
        """
        self.queryType = self.comboBox1.GetValue()
        if self.queryType == 'Bond':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.bondlist)
        elif self.queryType == 'Client':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.clientlist)
        elif self.queryType == 'Salesperson':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.saleslist)
        elif self.queryType == 'Issuer':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.issuerlist)
        elif self.queryType == 'Country':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.countrylist)
        else:
            pass

class MonthlyQuery(wx.Dialog):
    """Class to define the MonthlyQuery dialog box. Class is called when the 'Monthly Query' item in the Trade History
    menu is selected.

    Methods:
    __init__()
    editComboBox() 
    """
    def __init__(self, parent, mytitle):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, mytitle)
        """Keyword arguments:

        parent : mainframe
        mytitle : title of dialog box 
        """
        self.parent=parent
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        fgs = wx.FlexGridSizer(3, 2, 9, 25)        
        self.queryTypeLabel = wx.StaticText(self, label='Query type?')
        myChoices=['Bond','Client','Salesperson','Issuer','Country']
        self.queryType=myChoices[0]
        #self.comboBox1 = PromptingComboBox(self,myChoices[0],myChoices)
        self.comboBox1=wx.ComboBox(self, wx.ID_ANY, myChoices[0], style=wx.CB_DROPDOWN, choices=myChoices)
        sizerQueryType = wx.BoxSizer(wx.HORIZONTAL)
        sizerQueryType.Add(self.queryTypeLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerQueryType.Add(self.comboBox1, 0, wx.ALL|wx.CENTER, 5)
        self.queryIDLabel = wx.StaticText(self, label='ID?')
        myChoices=parent.bondlist
        self.comboBox2 = PromptingComboBox(self,myChoices[0],myChoices)
        self.Bind(wx.EVT_COMBOBOX, self.editComboBox2,self.comboBox1)
        sizerQueryID = wx.BoxSizer(wx.HORIZONTAL)
        sizerQueryID.Add(self.queryIDLabel, 0, wx.ALL|wx.CENTER, 5)
        sizerQueryID.Add(self.comboBox2, 0, wx.ALL|wx.CENTER, 5)
        fgs.AddMany([(self.queryTypeLabel), (self.comboBox1, 1, wx.EXPAND), (self.queryIDLabel), (self.comboBox2, 1, wx.EXPAND)])
        fgs.AddGrowableRow(2, 1)
        fgs.AddGrowableCol(1, 1)
        hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        okBtn = wx.Button(self, wx.ID_OK)
        vbox.Add(hbox,0,wx.ALL|wx.CENTER, 5)
        vbox.Add(okBtn,0,wx.ALL|wx.CENTER, 5)
        self.SetSizer(vbox)
        self.SetSizerAndFit(vbox)        
        self.Centre()

    def editComboBox2(self,event):
        """Function is called when an item in the combo box is selected.
        """
        self.queryType=self.comboBox1.GetValue()
        if self.queryType=='Bond':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.bondlist)
        elif self.queryType=='Client':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.clientlist)
        elif self.queryType=='Salesperson':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.saleslist)
        elif self.queryType=='Issuer':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.issuerlist)
        elif self.queryType=='Country':
            self.comboBox2.Clear()
            self.comboBox2.AppendItems(self.parent.countrylist)
        else:
            pass




class TradeActivityTabPanel(wx.Panel):
    """
    TradeActivityTabPanel class: Class to define the Trade Activity tab panel 
    """
    #----------------------------------------------------------------------
    def __init__(self, th, parentnotebook, mainframe):
        """
        Keyword argument:
        th : TradeHistory object, see TradeHistoryAnalysis.TradeHistory
        parentnotebook : wx.Python notebook object
        mainframe : wx.Python frame object
        """
        pub.subscribe(self.updatePositions, "POSITION_UPDATE")
        self.th = th
        self.parentnotebook = parentnotebook
        self.mainframe = mainframe
        wx.Panel.__init__(self, parent=parentnotebook)
        self.drawPanel()

    def lastUpdateString(self):
        """Defines lastUpdateString variable
        """
        if self.th.df['Date'].iloc[-1]!=datetime.datetime.today().strftime('%d/%m/%y'):
            return 'Last updated on ' + self.th.df['Date'].iloc[-1] + '. Select data and Ctrl-C to copy to the clipboard.'
        else:
            return 'Last updated today at ' + datetime.datetime.now().strftime('%H:%M') + '. Select data and Ctrl-C to copy to the clipboard.'

    def drawPanel(self):
        """Draws the trade activity panel 
        """
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.lastUpdateTime = wx.StaticText(self,-1,self.lastUpdateString())
        self.topSizer.Add(self.lastUpdateTime,0,wx.LEFT|wx.TOP,20)
        self.tradeActivityGrid = TradeActivityGrid(self,self.th)
        self.topSizer.Add(self.tradeActivityGrid,0,wx.LEFT,20)
        self.SetSizer(self.topSizer)
        self.Layout()
        pass

    def updatePositions(self,message=None):
        """event listener for the POSITION_UPDATE event. Updates position when the event is publicised 
        """
        self.tradeActivityGrid.fillGrid(self.mainframe.todayDT.strftime('%d/%m/%y'))
        self.lastUpdateTime.SetLabel(self.lastUpdateString())
        pass


class BondActivityTabPanel(wx.Panel):
    """
    BondActivityTabPanel class: Class to define the Bond Activity tab panel 
    """
    def __init__(self, th, ma, parentnotebook, mainframe):
        """
        Keyword argument:
        th : TradeHistory object, see TradeHistoryAnalysis.TradeHistory
        ma: MarketAxess history object
        parentnotebook : wx.Python notebook object
        mainframe : wx.Python frame object
        """

        self.th = th
        self.ma = ma
        self.parentnotebook = parentnotebook
        self.mainframe = mainframe
        wx.Panel.__init__(self, parent=parentnotebook)
        self.drawPanel()

    def lastUpdateString(self,bondname=''):
        """Defines lastUpdateString variable
        """
        output = 'Last 35 trades and MarketAxess enquiries (T-1)'
        if bondname=='':
            return output
        else:
            return output + ' for ' + bondname

    def drawPanel(self):
        """Draws the trade activity panel 
        """
        self.topSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.boxBondActivity = wx.StaticBox(self,label = 'Last 35 FRONT trades')
        self.boxMAActivity = wx.StaticBox(self,label = 'Last 35 MarketAxess enquiries (T-1)')
        self.sizerBondActivity = wx.StaticBoxSizer(self.boxBondActivity,wx.HORIZONTAL)
        self.sizerMAActivity = wx.StaticBoxSizer(self.boxMAActivity,wx.HORIZONTAL)
        self.bondActivityGrid=BondTradesGrid(self,self.th)
        self.marketAxessTradesGrid=MarketAxessTradesGrid(self,self.ma)
        self.sizerBondActivity.Add(self.bondActivityGrid,proportion=0,flag=wx.ALL,border=0)#,flag=wx.ALL)#expand
        self.sizerMAActivity.Add(self.marketAxessTradesGrid,proportion=0,flag=wx.ALL, border=0)#,flag=wx.ALL)#expand
        self.topSizer.Add(self.sizerBondActivity, 0, wx.ALL|wx.EXPAND, 20)
        self.topSizer.Add(self.sizerMAActivity, 0, wx.ALL|wx.EXPAND, 20)        
        self.SetSizer(self.topSizer)
        self.Layout()
        pass

    def fillGrid(self,bondname):
        wx.CallAfter(self.bondActivityGrid.fillGrid,bondname)
        wx.CallAfter(self.marketAxessTradesGrid.fillGrid,bondname)
        #self.lastUpdateTime.SetValue(self.lastUpdateString(bondname))
        self.boxBondActivity.SetLabel('Last 35 FRONT trades for ' + bondname)
        self.boxMAActivity.SetLabel('Last 35 MarketAxess enquiries (T-1) for ' + bondname)


class GenericDisplayGrid(gridlib.Grid):
    """
    Ctrl-C behaviour from http://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
    """
    def __init__(self,panel, nbrows, nbcols, colHeaders, colSizes, colAttrs, hScroll, vScroll):
        gridlib.Grid.__init__(self, panel)
        self.CreateGrid(nbrows,nbcols) 
        self.EnableEditing = True
        #rightalignattr = wx.grid.GridCellAttr()
        #rightalignattr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        wx.lib.colourdb.updateColourDB()
        self.oddLineColour = wx.NamedColour('GAINSBORO')
        self.oddlineattr = wx.grid.GridCellAttr()
        self.oddlineattr.SetBackgroundColour(self.oddLineColour)

        for i in range(0,nbcols):
            self.SetColLabelValue(i,colHeaders[i])
            self.SetColSize(i,colSizes[i])
            self.SetColAttr(i,colAttrs[i])
        self.ShowScrollbars(hScroll,vScroll)
        self.DisableDragRowSize()
        self.DisableDragColSize()
        wx.EVT_KEY_DOWN(self,self.onKey)
    pass

    def onKey(self, event):
        # If Ctrl+C is pressed...
        if event.ControlDown() and event.GetKeyCode() == 67:
            self.copy()
        event.Skip()

    def copy(self):
        # Number of rows and cols
        #print self.GetSelectionBlockBottomRight()
        #print self.GetGridCursorRow()
        #print self.GetGridCursorCol()
        if self.GetSelectionBlockTopLeft() == []:
            rows = 1
            cols = 1
            iscell = True
        else:
            rows = self.GetSelectionBlockBottomRight()[0][0] - self.GetSelectionBlockTopLeft()[0][0] + 1
            cols = self.GetSelectionBlockBottomRight()[0][1] - self.GetSelectionBlockTopLeft()[0][1] + 1
            iscell = False
        # data variable contain text that must be set in the clipboard
        data = ''
        # For each cell in selected range append the cell value in the data variable
        # Tabs '\t' for cols and '\r' for rows
        for r in range(rows):
            for c in range(cols):
                if iscell:
                    data += str(self.GetCellValue(self.GetGridCursorRow() + r, self.GetGridCursorCol() + c))
                else:
                    data += str(self.GetCellValue(self.GetSelectionBlockTopLeft()[0][0] + r, self.GetSelectionBlockTopLeft()[0][1] + c))
                if c < cols - 1:
                    data += '\t'
            data += '\n'
        # Create text data object
        clipboard = wx.TextDataObject()
        # Set data object value
        clipboard.SetText(data)
        # Put the data in the clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(clipboard)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Can't open the clipboard", "Error")


class TradeActivityGrid(GenericDisplayGrid):
    def __init__(self, panel, th):
        self.th = th
        colHeaders = ['Book','Bond','Quantity','Price','Counterparty','Sales','SC','MK','']
        colSizes = [75,100,75,75,100,75,50,50,18]
        dAttr = wx.grid.GridCellAttr()
        rAttr = wx.grid.GridCellAttr()
        rAttr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        colAttrs = [dAttr,dAttr,rAttr,rAttr,dAttr,dAttr,rAttr,rAttr,dAttr]
        GenericDisplayGrid.__init__(self,panel,250,9,colHeaders,colSizes,colAttrs,wx.SHOW_SB_NEVER,wx.SHOW_SB_DEFAULT)

    def fillGrid(self,date):
        subdfview = self.th.createOneDayTrades(date)
        rowindex = 0
        for (i,row) in subdfview.iterrows():
            if rowindex % 2:
                self.SetRowAttr(rowindex,self.oddlineattr.Clone())#this clone thing is needed in wxPython 3.0 (worked fine without in 2.8)
            self.SetCellValue(rowindex,0,row.iat[0])
            self.SetCellValue(rowindex,1,row.iat[1])
            self.SetCellValue(rowindex,2,'{:,.0f}'.format(row.iat[2]))
            self.SetCellValue(rowindex,3,'{:.4f}'.format(row.iat[3]))
            self.SetCellValue(rowindex,4,row.iat[4])
            self.SetCellValue(rowindex,5,str(row.iat[5]))
            self.SetCellValue(rowindex,6,'{:.1f}'.format(row.iat[6]))
            self.SetCellValue(rowindex,7,'{:.1f}'.format(row.iat[7]))
            rowindex = rowindex + 1
        self.SetCellValue(rowindex,0,'END')


class BondTradesGrid(GenericDisplayGrid):
    def __init__(self,panel,th):
        self.th = th
        colHeaders = ['Date','Quantity','Price','Counterparty','Sales','SC','MK']
        colSizes = [60,75,60,100,75,40,40]
        dAttr = wx.grid.GridCellAttr()
        rAttr = wx.grid.GridCellAttr()
        rAttr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        colAttrs = [rAttr,rAttr,rAttr,dAttr,dAttr,rAttr,rAttr]
        GenericDisplayGrid.__init__(self,panel,35,7,colHeaders,colSizes,colAttrs,wx.SHOW_SB_NEVER,wx.SHOW_SB_NEVER)
        pass

    def fillGrid(self,bond):
        self.ClearGrid()
        subdfview = self.th.df.loc[self.th.df['Bond']==bond,['Date','Qty','Price','Counterparty','Sales','SCu','MKu']].tail(35).copy()
        rowindex = 0
        for (i,row) in subdfview.iterrows():
            if rowindex % 2:
                self.SetRowAttr(rowindex,self.oddlineattr.Clone())#this clone thing is needed in wxPython 3.0 (worked fine without in 2.8)
            self.SetCellValue(rowindex,0,row.iat[0])
            self.SetCellValue(rowindex,1,'{:,.0f}'.format(row.iat[1]))
            self.SetCellValue(rowindex,2,'{:.4f}'.format(row.iat[2]))
            self.SetCellValue(rowindex,3,row.iat[3])
            self.SetCellValue(rowindex,4,str(row.iat[4]))
            self.SetCellValue(rowindex,5,'{:.1f}'.format(row.iat[5]))
            self.SetCellValue(rowindex,6,'{:.1f}'.format(row.iat[6]))
            rowindex = rowindex + 1


class MarketAxessTradesGrid(GenericDisplayGrid):
    def __init__(self, panel, ma):
        self.ma = ma
        colHeaders = ['Date','Counterparty','Side','Quantity','Status']
        colSizes = [60,100,60,75,100]
        dAttr = wx.grid.GridCellAttr()
        rAttr = wx.grid.GridCellAttr()
        rAttr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        colAttrs = [rAttr,dAttr,dAttr,rAttr,dAttr]
        GenericDisplayGrid.__init__(self,panel,35,5,colHeaders,colSizes,colAttrs,wx.SHOW_SB_NEVER,wx.SHOW_SB_NEVER)

    def fillGrid(self,bond):
        self.ClearGrid()
        subdfview = self.ma.df.loc[self.ma.df['Bond']==bond,['Date','Counterparty','Bid/Offer','AbsQty','Status']].tail(35).copy()
        rowindex = 0
        for (i,row) in subdfview.iterrows():
            if rowindex % 2:
                self.SetRowAttr(rowindex,self.oddlineattr.Clone())#this clone thing is needed in wxPython 3.0 (worked fine without in 2.8)
            self.SetCellValue(rowindex,0,row.iat[0].strftime('%d/%m/%y'))
            self.SetCellValue(rowindex,1,str(row.iat[1]))
            self.SetCellValue(rowindex,2,str(row.iat[2]))
            self.SetCellValue(rowindex,3,'{:,.0f}'.format(row.iat[3]*1000))
            self.SetCellValue(rowindex,4,str(row.iat[4]))
            rowindex = rowindex + 1
