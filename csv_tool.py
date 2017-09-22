import sys, os
import csv

import wx
import wx.grid
import pandas
from StaticDataImport import DEFPATH


class CSVTable(wx.grid.PyGridTableBase):
    def __init__(self, filename=None):
        self.filename = filename
        wx.grid.PyGridTableBase.__init__(self)
        oldcsvpd = pandas.read_csv(filename, header=None)
        (a,b) = oldcsvpd.shape
        self.csvpd = pandas.DataFrame(index=range(0,a+50), columns=range(0,b+20))
        for i in range(0,b):
            self.csvpd[i] = oldcsvpd[i]
        self.csvpd.fillna("", inplace=True)

    def save(self):
        newcsvpd = self.csvpd.copy()
        newcsvpd.dropna(0,how='all')
        newcsvpd.dropna(1,how='all')
        newcsvpd.to_csv(self.filename, header=False, index=False)

    def GetNumberRows(self):
        return len(self.csvpd.index)

    def GetNumberCols(self):
        return len(self.csvpd.columns)

    def IsEmptyCell(self, row, col):
        """Return True if the cell is empty"""
        return pandas.isnull(self.csvpd.iat[row, col])

    def GetTypeName(self, row, col):
        """Return the name of the data type of the value in the cell"""
        return wx.grid.GRID_VALUE_STRING

    def GetValue(self, row, col):
        return self.csvpd.iat[row,col]
    
    def SetValue(self, row, col, value):
        """Set the value of a cell"""
        self.csvpd.iat[row, col] = value


class CSVFrame(wx.Frame):
    def __init__(self, title):
        wx.Frame.__init__(self, None, size = (1024, 768), title=title)

        filename = title
        self.grid = wx.grid.Grid(self)
        self.table = CSVTable(filename = filename)
        self.grid.SetTable(self.table)
        self.grid.AutoSize()

        quitButton = wx.Button(self, label="Exit")
        quitButton.Bind(wx.EVT_BUTTON, self.onQuit)

        saveButton = wx.Button(self, label="Save")
        saveButton.Bind(wx.EVT_BUTTON, self.onSave)

        HS = wx.BoxSizer(wx.HORIZONTAL)
        HS.Add(quitButton, 1, wx.EXPAND, 5)
        HS.Add(saveButton, 1, wx.EXPAND, 5)
        
        VS = wx.BoxSizer(wx.VERTICAL)
        VS.Add(HS, 0, wx.EXPAND)
        VS.Add(self.grid, 0, wx.EXPAND)
        self.SetSizer(VS)

        self.Bind(wx.EVT_CLOSE, self.onQuit)
        
    def onQuit(self,Event):
        self.Destroy()
        
    def onSave(self, event=None):
        self.table.save()
            
        
class MyApp(wx.App):
    def __init__(self, *args, **kwargs):
        wx.App.__init__(self, *args, **kwargs)
        
        # This catches events when the app is asked to activate by some other
        # process
        self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

    def OnInit(self):

        self.frame = CSVFrame(title = DEFPATH+'genericSettings.csv')
        self.frame.Show()
        return True

    def BringWindowToFront(self):
        try: # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except:
            pass
        
    def OnActivate(self, event):
        # if this is an activate event, rather than something else, like iconize.
        if event.GetActive():
            self.BringWindowToFront()
        event.Skip()
     

if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()



