#----------------------------------------------------------------------
# Name:        Inspector.py
# Purpose:     
#
# Author:      Riaan Booysen
#
# Created:     1999
# RCS-ID:      $Id$
# Copyright:   (c) 1999, 2000 Riaan Booysen
# Licence:     GPL
#----------------------------------------------------------------------

""" Inspects and edits design-time components, manages property editors 
    and interacts with the designer and companions
    
    XXX Todo XXX
    
    * write/wrap many more classes
    * consider either 
      * splitting pygasm structure from inspector gui
      * having InspectorScrollWin base class
    * Update speed
      * draw inspead of having panels for thin line
      * just in time show/hiding instead of recreating editor controls

"""

# New sizes palette 140 high, inspector/debugger 230 wide 

# XXX replace all this silly resizing logic with sizers

# XXX write ctrl cache for inspector name value divider controls
# XXX Expanding ???

from wxPython.wx import *
import PaletteMapping, PropertyEditors, sender, Preferences, Help
#import Debug
#import types
from types import *
from RTTI import *
from EventCollections import *
from Utils import AddToolButtonBmpFile

oiLineHeight = 18
oiNamesWidth = 100

wxID_PARENTTREE = NewId()
wxID_PARENTTREESELECTED = NewId()
class ParentTree(wxTreeCtrl):
    # XXX Rather associate data with tree item rather than going only on the name
    def __init__(self, parent):
        wxTreeCtrl.__init__(self, parent, wxID_PARENTTREE)
        self.cleanup()
        EVT_TREE_SEL_CHANGED(self, wxID_PARENTTREE, self.OnSelect)
            
    def cleanup(self):
        self.designer = None
        self.valid = false
        self.treeItems = {}
        self.DeleteAllItems()
 
                                
    def addChildren(self, parent, dict, designer):
        for par in dict.keys():
            img = PaletteMapping.compInfo[designer.objects[par][1].__class__][2]
            itm = self.AppendItem(parent, par, img)
            self.treeItems[par] = itm
            if len(dict[par]):
                self.addChildren(itm, dict[par], designer)
        self.Expand(parent)
                
        
    def refreshCtrl(self, root, relDict, designer):
        self.cleanup()
        self.designer = designer
        self.root = self.AddRoot(root, 
     PaletteMapping.compInfo[designer.objects[''][1].__class__.__bases__[0]][2])
        
        self.treeItems[''] = self.root
        self.addChildren(self.root, relDict[''], designer)
        
        self.valid = true
    
    def selectName(self, name):
        self.SelectItem(self.treeItems[name])
    
    def selectedName(self):
        return self.GetItemText(self.GetSelection())

    def selectItemGUIOnly(self, name):
        self.SelectItem(self.treeItems[name])
    
    def extendHelpUrl(self, url):
        return url

    def OnSelect(self, event):
        """ Event triggered when the selection changes in the tree """ 
        if self.valid: 
            idx = self.GetSelection()
            if self.designer:
#                if idx == self.root:
#                if self.GetRootItem() == idx:
                # Ugly but nothing else works
                try:    		
                    ctrlInfo = self.designer.objects[self.GetItemText(idx)]
                except KeyError:
                    ctrlInfo = self.designer.objects['']
            
                if self.designer.selection:
                    self.designer.selection.selectCtrl(ctrlInfo[1], ctrlInfo[0])
    
        
class NameValue:
    def __init__(self, inspector, nameParent, valueParent, companion, 
      rootCompanion, name, getsetters, idx, indent, 
      editor = None, options = None, names = None):
	self.destr = false
        self.lastSizeN = 0
        self.lastSizeV = 0
        self.indent = indent
        self.inspector = inspector
        self.propName = name
#        self.obj = obj
#        self.root = root
	
        self.nameParent = nameParent
        self.valueParent = valueParent
        self.idx = idx
        self.nameBevelTop = None
        self.nameBevelBottom = None
        self.valueBevelTop = None
        self.valueBevelBottom = None
        
        if editor:
            self.propEditor = editor(name, valueParent, companion, rootCompanion, getsetters, 
              idx, valueParent.GetSize().y - 20, options, names)
        else:    
            self.propEditor = PropertyEditors.propertyRegistry.factory(name, 
              valueParent, companion, rootCompanion, getsetters, idx, 
              valueParent.GetSize().y - 20)
	
	self.expander = None
	if self.propEditor: 
	    self.propValue = self.propEditor.getValue()
	    displayVal = self.propEditor.getDisplayValue()

	    # check if it's expandable
	    if self.propEditor.getStyle().count(PropertyEditors.esExpandable):
	        mID = NewId()
	        self.expander = wxCheckBox(nameParent, mID, '', 
	          wxPoint(8 * self.indent, self.idx * oiLineHeight +2), 
	          wxSize(12, 14))
	        self.expander.SetValue(true)
	        EVT_CHECKBOX(self.expander, mID, self.OnExpand)
	else: 
	    self.propValue = ''
	    displayVal = ''
	
        self.name = wxStaticText(nameParent, -1, name, wxPoint(8 * self.indent + 16, idx * oiLineHeight +2), wxSize(inspector.panelNames.GetSize().x, oiLineHeight -3), style = wxCLIP_CHILDREN)
        EVT_LEFT_DOWN(self.name, self.OnSelect)
        self.value = wxStaticText(valueParent, -1, displayVal, wxPoint(2, idx * oiLineHeight +2), wxSize(inspector.getValueWidth(), oiLineHeight -3), style = wxCLIP_CHILDREN)
        self.value.SetForegroundColour(wxColour(0, 0, 100))
        EVT_LEFT_DOWN(self.value, self.OnSelect)

        self.separatorN = wxPanel(nameParent, -1, wxPoint(0, (idx +1) * oiLineHeight), wxSize(inspector.panelNames.GetSize().x, 1), style = wxCLIP_CHILDREN)
        self.separatorN.SetBackgroundColour(wxColour(160, 160, 160))
        self.separatorV = wxPanel(valueParent, -1, wxPoint(0, (idx +1) * oiLineHeight), wxSize(inspector.getValueWidth(), 1), style = wxCLIP_CHILDREN)
        self.separatorV.SetBackgroundColour(wxColour(160, 160, 160))
        
    def destroy(self, cancel = false):
        self.hideEditor(cancel)
	self.destr = true
        self.name.Destroy()
        self.value.Destroy()
        self.separatorN.Destroy()
        self.separatorV.Destroy()
        if self.expander:
            self.expander.Destroy()
            
    def setPos(self, idx):
        self.idx = idx
        if self.expander:
            self.expander.SetPosition(wxPoint(8 * self.indent, self.idx * oiLineHeight))
        self.name.SetPosition(wxPoint(8 * self.indent + 16, idx * oiLineHeight +2))
        self.value.SetPosition(wxPoint(2, idx * oiLineHeight +2))
        self.separatorN.SetPosition(wxPoint(0, (idx +1) * oiLineHeight))
        self.separatorV.SetPosition(wxPoint(0, (idx +1) * oiLineHeight))
        if self.nameBevelTop:
            self.nameBevelTop.SetPosition(wxPoint(0, idx*oiLineHeight -1))
            self.nameBevelBottom.SetPosition(wxPoint(0, (idx + 1)*oiLineHeight -1))
        if self.propEditor:
            self.propEditor.setIdx(idx)
        elif self.valueBevelTop:
            self.valueBevelTop.SetPosition(wxPoint(0, idx*oiLineHeight -1))
            self.valueBevelBottom.SetPosition(wxPoint(0, (idx + 1)*oiLineHeight -1))
            
    def resize(self, nameWidth, valueWidth):
        if nameWidth <> self.lastSizeN:
            if self.nameBevelTop:
                self.nameBevelTop.SetSize(wxSize(nameWidth, 1))
                self.nameBevelBottom.SetSize(wxSize(nameWidth, 1))
                
            if nameWidth > 100:
                self.name.SetSize(wxSize(nameWidth, self.name.GetSize().y))
            else:
                self.name.SetSize(wxSize(100, self.name.GetSize().y))
                
            self.separatorN.SetSize(wxSize(nameWidth, 1))        

        if valueWidth <> self.lastSizeV:
            if self.valueBevelTop:
                self.valueBevelTop.SetSize(wxSize(valueWidth, 1))
                self.valueBevelBottom.SetSize(wxSize(valueWidth, 1))

    	    self.value.SetSize(wxSize(valueWidth, self.value.GetSize().y))

            self.separatorV.SetSize(wxSize(valueWidth, 1))

            if self.propEditor:
                self.propEditor.setWidth(valueWidth)

        self.lastSizeN = nameWidth
        self.lastSizeV = valueWidth
            
    def showEdit(self):
        self.nameBevelTop = wxPanel(self.nameParent, -1, wxPoint(0, self.idx*oiLineHeight -1), wxSize(self.inspector.panelNames.GetSize().x, 1))
        self.nameBevelTop.SetBackgroundColour(wxBLACK)
        self.nameBevelBottom = wxPanel(self.nameParent, -1, wxPoint(0, (self.idx + 1)*oiLineHeight -1), wxSize(self.inspector.panelNames.GetSize().x, 1))
        self.nameBevelBottom.SetBackgroundColour(wxWHITE)
        if self.propEditor:
            self.value.SetLabel('')
	    self.propEditor.inspectorEdit()	            
  	else:
            self.valueBevelTop = wxPanel(self.valueParent, -1, wxPoint(0, self.idx*oiLineHeight -1), wxSize(self.inspector.getValueWidth(), 1))
            self.valueBevelTop.SetBackgroundColour(wxBLACK)
            self.valueBevelBottom = wxPanel(self.valueParent, -1, wxPoint(0, (self.idx + 1)*oiLineHeight -1), wxSize(self.inspector.getValueWidth(), 1))
            self.valueBevelBottom.SetBackgroundColour(wxWHITE)

    def hideEditor(self, cancel = false):
        if self.nameBevelTop:
            self.nameBevelTop.Destroy()
            self.nameBevelTop = None
            self.nameBevelBottom.Destroy()
            self.nameBevelBottom = None
           
        if self.valueBevelTop:
            self.valueBevelTop.Destroy()
            self.valueBevelTop = None
            self.valueBevelBottom.Destroy()
            self.valueBevelBottom = None
       
        if (not cancel) and self.propEditor:# and (not self.destr):
            self.propEditor.inspectorPost()
	    self.value.SetLabel(self.propEditor.getDisplayValue())            
    	    self.value.SetSize(wxSize(self.separatorV.GetSize().x, self.value.GetSize().y))
	    
    def OnSelect(self, event):
        self.inspector.propertySelected(self)
    
    def OnExpand(self, event):
        if event.Checked(): self.inspector.collapse(self)
        else: self.inspector.expand(self)

class PropNameValue(NameValue):
    def initFromComponent(self):
        if self.propEditor: 
            self.propEditor.initFromComponent()
            if not self.propEditor.editorCtrl:
                self.value.SetLabel(self.propEditor.getDisplayValue())
            self.propEditor.persistValue(self.propEditor.valueAsExpr())

class ConstrNameValue(NameValue):
    pass

class EventNameValue(NameValue):
    def initFromComponent(self):
        if self.propEditor: 
            self.propEditor.initFromComponent()
            if not self.propEditor.editorCtrl:
                self.value.SetLabel(self.propEditor.getDisplayValue())

class EventsWindow(wxSplitterWindow):
    def __init__(self, parent, inspector):
        wxSplitterWindow.__init__(self, parent, -1)
	self.inspector = inspector
        
        self.categories = wxSplitterWindow(self, -1, style = wxSP_NOBORDER)
        self.definitions = InspectorEventScrollWin(self, inspector)
        
        self.SetMinimumPaneSize(20)
        self.SplitHorizontally(self.categories, self.definitions)
        self.SetSashPosition(100)
        
        self.categoryClasses = wxListCtrl(self.categories, 100, style = wxLC_LIST)
        self.selCatClass = -1
        EVT_LIST_ITEM_SELECTED(self.categoryClasses, 100, self.OnCatClassSelect) 
        EVT_LIST_ITEM_DESELECTED(self.categoryClasses, 100, self.OnCatClassDeselect)

        self.categoryMacros = wxListCtrl(self.categories, 101, style = wxLC_LIST)
        EVT_LIST_ITEM_SELECTED(self.categoryMacros, 101, self.OnMacClassSelect) 
        EVT_LIST_ITEM_DESELECTED(self.categoryMacros, 101, self.OnMacClassDeselect)
        EVT_LEFT_DCLICK(self.categoryMacros, self.OnMacroSelect) 

        f = self.categoryMacros.GetFont()
        f.SetPointSize(f.GetPointSize() -5)
        self.categoryMacros.SetFont(f)
        self.selMacClass = -1

        self.categories.SetMinimumPaneSize(20)
        self.categories.SplitVertically(self.categoryClasses, self.categoryMacros)
        self.categories.SetSashPosition(80)
        
        tPopupIDAdd = 15
        tPopupIDDelete = 16
        self.menu = wxMenu()
        self.menu.Append(tPopupIDAdd, "Add")
        self.menu.Append(tPopupIDDelete, "Delete")
        EVT_MENU(self, tPopupIDAdd, self.OnAdd)
        EVT_MENU(self, tPopupIDDelete, self.OnDelete)

    def readObject(self):
        #clean up all previous items
        self.cleanup()
        
        # List available categories
        for catCls in self.inspector.selCmp.events():
            self.categoryClasses.InsertStringItem(0, catCls)
        
        vs = self.definitions.GetVirtualSize()
        self.definitions.panelNames.SetSize(wxSize(oiNamesWidth, vs[1]))
        self.definitions.panelValues.SetSize(wxSize(vs[0] - oiNamesWidth, vs[1]))

        self.definitions.readObject()
        
        self.definitions.refreshSplitter()

#	self.definitions.splitter.SetSize(wxSize(self.definitions.GetSize().x, len(self.definitions.nameValues) *18 + 1))
    def cleanup(self):
        self.definitions.cleanup()
        self.categoryClasses.DeleteAllItems()
        self.categoryMacros.DeleteAllItems()
        
    
    def findMacro(self, name):
        for macro in EventCategories[self.categoryClasses.GetItemText(self.selCatClass)]:
            if macro.func_name == name: return macro
        raise 'Macro: '+name+' not found.'

    def addEvent(self, name, value, id = None):
        self.inspector.selCmp.persistEvt(name, value, id)
        self.inspector.selCmp.evtSetter(name, value)
        
        self.definitions.addEvent(name)
	self.definitions.refreshSplitter()

    def getEvent(self, name):
        return self.definitions.getNameValue(name)
            	    
    def macroNameToEvtName(self, macName):
        flds = string.splitfields(macName, '_')
        del flds[0] #remove 'EVT'
        evtName = 'On'+string.capitalize(self.inspector.selObj.GetName())
        for fld in flds:
            evtName = evtName + string.capitalize(fld)
        return evtName
    
    def extendHelpUrl(self, url):
        return url
    
    def OnCatClassSelect(self, event):
        self.selCatClass = event.m_itemIndex
        catClass = EventCategories[self.categoryClasses.GetItemText(self.selCatClass)]
        for catMac in catClass:
            self.categoryMacros.InsertStringItem(0, catMac.func_name)
        
    def OnCatClassDeselect(self, event):
        self.selCatClass = -1
        self.selMacClass = -1
        self.categoryMacros.DeleteAllItems()

    def OnMacClassSelect(self, event):
        self.selMacClass = event.m_itemIndex
        
    def OnMacClassDeselect(self, event):
        self.selMacClass = -1
    
    def OnMacroSelect(self, event):
        if self.selMacClass > -1:
            companion = self.inspector.selCmp
            macName = self.categoryMacros.GetItemText(self.selMacClass)
            methName = self.macroNameToEvtName(macName)
            catClassName = self.categoryClasses.GetItemText(self.selCatClass)
            frameName = companion.designer.GetName()
            if catClassName in commandCategories:
                id = companion.id
            else:
                id = None
            nv = self.getEvent(macName[4:])
            if nv:
                self.addEvent(macName[4:], methName, id)
                nv.initFromComponent()
                nv.OnSelect(None)

            else: self.addEvent(macName[4:], methName, id)

    def OnAdd(self, event):
        self.OnMacroSelect(event)
    
    def OnDelete(self, event):
        if self.selMacClass > -1:
            macName = self.categoryMacros.GetItemText(self.selMacClass)
            print 'mac delete', macName
            self.addEvent(macName[4:], methName)
        
    

# When a namevalue in the inspector is clicked (selected) the following happens
# * Active property editor is hidden, data posted, controls freed
# * New namevalue's propertyeditor creates an editor

class NameValueEditorScrollWin(wxScrolledWindow):
    def __init__(self, parent):
        wxScrolledWindow.__init__(self, parent, -1, wxPoint(0, 0), wxPyDefaultSize, wxSUNKEN_BORDER)
        self.SetBackgroundColour(wxColour(160, 160, 160))
	self.nameValues = []
        self.prevSel = None
        self.splitter = wxSplitterWindow(self, -1, wxPoint(0, 0), parent.GetSize(), wxSP_NOBORDER)#wxSP_3D)#

        self.panelNames = wxPanel(self.splitter, -1, wxDefaultPosition, wxSize(100, 1))
        EVT_SIZE(self.panelNames, self.OnNameSize)   
        self.panelValues = wxPanel(self.splitter, -1)
        EVT_SIZE(self.panelValues, self.OnNameSize)   

        self.splitter.SplitVertically(self.panelNames, self.panelValues)
        self.splitter.SetSashPosition(100)
        self.splitter.SetMinimumPaneSize(20)
        
        EVT_SIZE(self, self.OnSize)   
	
    def cleanup(self):
        # XXX Does this always have to be inited here?
        self.prevSel = None
        #clean up
        for i in self.nameValues:
            i.destroy()
        self.nameValues = []

    def getNameValue(self, name):
        for nv in self.nameValues:
            if nv.propName == name:
                return nv
        return None
                 	
    def getWidth(self):
        return self.GetSize().x

    def getHeight(self):
        return len(self.nameValues) *20
    
    def getValueWidth(self):
        return self.GetSize().x - 24 - self.panelNames.GetSize().x
        
    def refreshSplitter(self):
	self.splitter.SetSize(wxSize(self.GetSize().x - 24, len(self.nameValues) *oiLineHeight + 1))
        height = len(self.nameValues)

    def propertySelected(self, nameValue):
        """ Called when a new name value is selected """
        if self.prevSel:
            self.prevSel.hideEditor()
    	nameValue.showEdit()
    	self.prevSel = nameValue

    def resizeNames(self):	
        for nv in self.nameValues:
           nv.resize(self.panelNames.GetSize().x, self.getValueWidth())

    def OnSize(self, event):
        self.refreshSplitter()
        event.Skip()
	
    def OnNameSize(self, event):
        self.resizeNames()
        event.Skip()
        
    
class InspectorScrollWin(NameValueEditorScrollWin):
    def __init__(self, parent, inspector):
        NameValueEditorScrollWin.__init__(self, parent)
	self.inspector = inspector
	
	self.EnableScrolling(false, true)
	# ?
	self.expanders = sender.SenderMapper()

        self.selObj = inspector.selObj
        self.selCmp = inspector.selCmp
        
        self.prevSel = None

    def deleteNameValues(self, idx, count, cancel = false):
        # delete sub properties
        deleted = 0
        if idx < len(self.nameValues):
            while (idx < len(self.nameValues)) and (deleted < count):
                if self.nameValues[idx] == self.prevSel: self.prevSel = None
	        self.nameValues[idx].destroy(cancel)
	        del self.nameValues[idx]
	        deleted = deleted + 1

	if idx + 1 < len(self.nameValues):
            # move properties up
            for idx in range(idx, len(self.nameValues)):
                self.nameValues[idx].setPos(idx)

    def extendHelpUrl(self, url):
        return url

class InspectorPropScrollWin(InspectorScrollWin):
    def setNameValues(self, compn, rootCompn, nameValues, insIdx, indent):
    	top = insIdx
    	
    	# Add NameValues to panel
    	for nameValue in nameValues:
    	    # Check if there is an associated companion	
            if compn: 
                self.nameValues.insert(top, PropNameValue(self, self.panelNames, 
                  self.panelValues, compn, rootCompn, nameValue[0], nameValue[1], top, indent, 
                  compn.getPropEditor(nameValue[0]), 
                  compn.getPropOptions(nameValue[0]), 
                  compn.getPropNames(nameValue[0])))
	    top = top + 1

	self.refreshSplitter()

    def extendHelpUrl(self, url):
        if self.prevSel:
            suburl = 'get'+string.lower(self.prevSel.name)
        return url + '#' + suburl

#XXX only companion should be passed around, companion contains the controlx

    # read in the root object
    def readObject(self, propList):
        self.cleanup()

	# create root list
	self.setNameValues(self.inspector.selCmp, self.inspector.selCmp, 
	  propList, 0, 0)
        
        height = len(self.nameValues)
        self.SetScrollbars(oiLineHeight, oiLineHeight, 0, height + 1)
# temp remark
#        vs = self.GetVirtualSize()
#        self.panelNames.SetSize(wxSize(oiNamesWidth, vs[1]))
#        self.panelValues.SetSize(wxSize(vs[0] - oiNamesWidth, vs[1]))

    def expand(self, nameValue):
#        self.readObject(self.nameValues[nameValue.idx].propValue)
                
        obj = self.nameValues[nameValue.idx].propValue
        
        if PaletteMapping.helperClasses.has_key(obj.__class__.__name__):
            # XXX passing a None designer
            compn = PaletteMapping.helperClasses[obj.__class__.__name__](nameValue.propName, 
              None, self.inspector.selObj, obj)
        
            propLst = getPropList(obj, compn)['properties']
            sze = len(propLst)
           
            indt = self.nameValues[nameValue.idx].indent + 1
            
            # move properties down
            startIdx = nameValue.idx + 1
            for idx in range(startIdx, len(self.nameValues)):
                self.nameValues[idx].setPos(idx +sze)
	    	    
	    # add sub properties in the gap
	    self.setNameValues(compn, self.inspector.selCmp, propLst, startIdx, indt)
	
    def collapse(self, nameValue):
        # delete all NameValues until the same indent, count them
        startIndent = nameValue.indent
        idx = nameValue.idx + 1
                
#        Move deletion into method and use in removeEvent of EventWindow
        i = idx
        if i < len(self.nameValues):
            while (i < len(self.nameValues)) and \
              (self.nameValues[i].indent > startIndent):
                i = i + 1
        count = i - idx
        
        self.deleteNameValues(idx, count)
                	        
class InspectorConstrScrollWin(InspectorScrollWin):
    # read in the root object
    def readObject(self, constrList):
        def findInConstrLst(name, constrList):
            for constr in constrList:
                if constr[0] == name:
                    return constr[1]
            return None
            
        self.cleanup()
        
        params = self.inspector.selCmp.constructor()
        paramNames = params.keys()
        paramNames.sort()
        
        for param in paramNames:
            propmeths = findInConstrLst(param, constrList)
            if propmeths: self.addProp(param, propmeths)
            else: self.addConstr(param)
            
	self.refreshSplitter()


    def addConstr(self, name):
        compn = self.inspector.selCmp
        self.nameValues.insert(len(self.nameValues), 
          ConstrNameValue(self, self.panelNames, 
          self.panelValues, self.inspector.selCmp, self.inspector.selCmp, name, 
          (None, None),
          len(self.nameValues), 0, 
          compn.getPropEditor(name), 
          compn.getPropOptions(name), 
          compn.getPropNames(name)))
#          PropertyEditors.ConstrPropEdit))


    def addProp(self, name, getSets):
        compn = self.inspector.selCmp
        self.nameValues.insert(len(self.nameValues), 
          PropNameValue(self, self.panelNames, self.panelValues, 
          compn, compn, 
          name, getSets, len(self.nameValues), 0, 
          compn.getPropEditor(name), 
          compn.getPropOptions(name), 
          compn.getPropNames(name)))
    
class InspectorEventScrollWin(InspectorScrollWin):
    def readObject(self):
        self.cleanup()
        
        for evt in self.inspector.selCmp.textEventList:
            self.addEvent(evt.event_name)

        height = len(self.nameValues)
        self.SetScrollbars(oiLineHeight, oiLineHeight, 0, height + 1)

	self.refreshSplitter()

    def addEvent(self, name):
        nv = self.getNameValue(name)
        if nv: nv.initFromComponent()
        else:
            self.nameValues.insert(len(self.nameValues), 
              EventNameValue(self, self.panelNames, 
              self.panelValues, self.inspector.selCmp, self.inspector.selCmp, name, 
              (self.inspector.selCmp.evtGetter, self.inspector.selCmp.evtSetter),
              len(self.nameValues), -2, PropertyEditors.EventPropEdit))

        self.refreshSplitter()
    def removeEvent(self, name):
        # This event will always be selected by a property editor in edit mode
        # therefor nothing will be selected after this
        
        nv = self.getNameValue(name)
        self.deleteNameValues(nv.idx, 1, true)
        self.prevSel = None
        
#def addToolButton(frame, toolbar, filename, hint, triggermeth):
#    nId = NewId()
#    toolbar.AddTool(nId, wxBitmap(filename, wxBITMAP_TYPE_BMP), 
#      shortHelpString = hint)
#    EVT_TOOL(frame, nId, triggermeth)

class InspectorNotebook(wxNotebook):
    def __init__(self, parent):
        wxNotebook.__init__(self, parent, -1)
        self.pages = {}

    def AddPage(self, window, name):
        wxNotebook.AddPage(self, window, name)
        self.pages[name] = window

    def extendHelpUrl(self, name):
	 return self.pages[name].extendHelpUrl(url)   

class InspectorFrame(wxFrame):
    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, -1, title, 
          wxPoint(0, Preferences.paletteHeight + Preferences.windowManagerTop + \
          Preferences.windowManagerBottom), wxSize(Preferences.inspWidth, 
          Preferences.bottomHeight))

        self.paletteImages = wxImageList(24, 24)

        for cmpInf in PaletteMapping.compInfo.values():
            cmpInf.append(self.paletteImages.Add(wxBitmap('Images/Palette/Gray/'+\
              cmpInf[0]+'.bmp', wxBITMAP_TYPE_BMP)))
        
        self.statusBar = self.CreateStatusBar()
        self.statusBar.SetFont(wxFont(Preferences.inspStatBarFontSize, wxDEFAULT, wxNORMAL, wxBOLD, false))

        if wxPlatform == '__WXMSW__':
            self.icon = wxIcon('Images/Icons/Inspector.ico', wxBITMAP_TYPE_ICO)
            self.SetIcon(self.icon)
	
        EVT_SIZE(self, self.OnSizing)

        self.selObj = None
        self.selCmp = None
        self.prevDesigner = None 
        
        self.toolBar = self.CreateToolBar(wxTB_HORIZONTAL|wxNO_BORDER)#|wxTB_FLAT

        AddToolButtonBmpFile(self, self.toolBar, 'Images/Inspector/Up.bmp', 'Select parent', self.OnUp)
        self.toolBar.AddSeparator()
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Shared/Delete.bmp', 'Delete selection', self.OnDelete)
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Shared/Cut.bmp', 'Cut (not implemented)', self.OnCut)
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Shared/Copy.bmp', 'Copy (not implemented)', self.OnCopy)
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Shared/Paste.bmp', 'Paste (not implemented)', self.OnPaste)
        self.toolBar.AddSeparator()
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Inspector/Post.bmp', 'Post', self.OnPost)
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Inspector/Cancel.bmp', 'Cancel', self.OnCancel)
        self.toolBar.AddSeparator()
        AddToolButtonBmpFile(self, self.toolBar, 'Images/Shared/Help.bmp', 'Show help', self.OnHelp)
        self.toolBar.Realize()

        self.pages = InspectorNotebook(self)

        self.constr = InspectorConstrScrollWin(self.pages, self)
        self.pages.AddPage(self.constr, 'Constructor')
	
        self.props = InspectorPropScrollWin(self.pages, self)
        self.pages.AddPage(self.props, 'Properties')

        self.events = EventsWindow(self.pages, self)
        self.pages.AddPage(self.events, 'Events')

        self.containment = ParentTree(self.pages)
        self.containment.SetImageList(self.paletteImages)
        self.pages.AddPage(self.containment, 'Parents')
 	
 	self.selection = None
        self.pages.ResizeChildren()
            
    def selectObject(self, obj, compn, selectInContainment = true):
        if self.selObj == obj and self.selCmp == compn:
            return

        if self.prevDesigner and compn.designer and compn.designer != self.prevDesigner \
          and hasattr(self.prevDesigner, 'selection'):
            if compn.designer.supportsParentView:  
                compn.designer.refreshContainment()

        self.prevDesigner = compn.designer

        self.selObj = obj
        self.selCmp = compn

        self.statusBar.SetStatusText(compn.name)
        # Update progress inbetween building of property pages
        # Is this convoluted or what :)
        sb = self.selCmp.designer.model.editor.statusBar.progress
        sb.SetValue(10)
        c_p = getPropList(obj, compn)
        sb.SetValue(30)
        self.constr.readObject(c_p['constructor'])
        sb.SetValue(50)
        self.props.readObject(c_p['properties'])
        sb.SetValue(70)
        self.events.readObject()
        sb.SetValue(90)
        
        if selectInContainment and self.containment.valid: 
            # XXX Ugly must change
            try:
	         treeId = self.containment.treeItems[compn.name]
            except:
	         treeId = self.containment.treeItems['']
		
##            if obj == compn.designer: treeId = self.containment.treeItems['']
##            else: treeId = self.containment.treeItems[compn.name]
            
            self.containment.valid = false
            self.containment.SelectItem(treeId)
            self.containment.valid = true
            self.containment.EnsureVisible(treeId)

        sb.SetValue(0)

        self.pages.ResizeChildren()
    
    def pageUpdate(self, page, name):
	nv = page.getNameValue(name)
        if nv: nv.initFromComponent()
    def propertyUpdate(self, name):
        self.pageUpdate(self.props, name)
    def constructorUpdate(self, name):
        self.pageUpdate(self.constr, name)
    def eventUpdate(self, name, delete = false):
        if delete:
            self.events.definitions.removeEvent(name)
        else:
            self.pageUpdate(self.events, name)

    def selectedCtrlHelpFile(self):
        if self.selCmp: return self.selCmp.wxDocs
        else: return ''
            
    def cleanup(self):
        self.selCmp = None
        self.selObj = None
        self.constr.cleanup()
        self.props.cleanup()
        self.events.cleanup()
#        self.containment.cleanup()
        self.statusBar.SetStatusText('')

    def OnCloseWindow(self, event):
    	self.Show(false)
    	
    def OnSizing(self, event):
#        self.debugger.log(`self.GetSize()`)
        event.Skip()
    
    def OnDelete(self, event):
        if self.selCmp:
            self.selCmp.designer.deleteCtrl(self.selCmp.name)
##            if self.pages.GetPageText(self.pages.GetSelection()) == 'Parents':
##                self.containment.SetFocus()
    
    def OnUp(self, event):
        if self.selCmp:
            self.selCmp.designer.selectParent(self.selObj)

    def OnCut(self, event):
        pass
    def OnCopy(self, event):
        pass
    def OnPaste(self, event):
        pass
    
    def OnPost(self, event):
        if self.selCmp:
            self.selCmp.designer.saveOnClose = true
            self.selCmp.designer.Close()
    
    def OnCancel(self, event):
        if self.selCmp:
            self.selCmp.designer.saveOnClose = false
            self.selCmp.designer.Close()

    def OnHelp(self, event):
        if self.selCmp:
            url = self.pages.extendHelpUrl(self.selectedCtrlHelpFile())
            Help.showHelp(self, Help.wxWinHelpFrame, url)
#            Preferences.toWxDocsPath(self.selectedCtrlHelpFile()), 'wxWinHelp.ico')
        else:
            Help.showHelp(self, Help.BoaHelpFrame, 'Inspector.html')
#            Help.showHelp(self, Preferences.toPyPath('Docs/Inspector.html'), 'Help.ico')

    def OnCloseWindow(self, event):
        self.cleanup()
        event.Skip()


