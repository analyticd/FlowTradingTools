import wx

class TestNoteBook(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, size=(600, 500))
        panel = wx.Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        toppanel = wx.Panel(panel)
        bottompanel = wx.Panel(panel)
        notebook = wx.Notebook(bottompanel)
        posterpage = wx.Panel(notebook)
        listpage = wx.Panel(notebook)
        notebook.AddPage(posterpage, 'posters')
        notebook.AddPage(listpage, 'list')

        sizer1 = wx.BoxSizer(wx.VERTICAL)
        sizer2 = wx.BoxSizer(wx.VERTICAL)
        btn = wx.Button(toppanel, label="Refresh Front data")
        sizer1.Add(btn,1, wx.EXPAND, 2)
        txt = wx.TextCtrl(toppanel,-1,'this is a test')
        sizer1.Add(txt,1, wx.EXPAND, 2)
        toppanelsizer=wx.BoxSizer(wx.VERTICAL)
        toppanelsizer.Add(sizer1,0, wx.ALL|wx.EXPAND, 2)
        toppanelsizer.Add(sizer2,0, wx.ALL|wx.EXPAND, 2)
        toppanel.SetSizer(toppanelsizer)
        toppanel.Layout()
        
        vsizer.Add(toppanel, 0.25, wx.EXPAND)
        vsizer.Add(bottompanel, 1, wx.EXPAND)
        #vsizer.Add(sizer1, 1, wx.EXPAND)

        ##### Added code (
        bottompanel_sizer = wx.BoxSizer(wx.VERTICAL)
        bottompanel_sizer.Add(notebook, 1, wx.EXPAND)
        bottompanel.SetSizer(bottompanel_sizer)

        toppanel.SetBackgroundColour('blue') # not needed, to distinguish bottompanel from toppanel
        ##### Added code )

        panel.SetSizer(vsizer)


app = wx.App()
frame = TestNoteBook(None, -1, 'notebook')
frame.Show()
app.MainLoop()