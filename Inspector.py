#----------------------------------------------------------------------
# Name:        Inspector.py
# Purpose:
#
# Author:      Riaan Booysen
#
# Created:     1999
# RCS-ID:      $Id$
# Copyright:   (c) 1999 - 2005 Riaan Booysen
# Licence:     GPL
#----------------------------------------------------------------------
#Boa:Frame:InspectorFrame

""" Inspects and edits design-time components, manages property editors
    and interacts with the designer and companions
"""

print 'importing Inspector'

# XXX Disable clipboards buttons when non Designer item is selected !!

import os
from types import *

from wxPython.wx import *
from wxPython.lib.stattext import wxGenStaticText

import PaletteMapping, PaletteStore, Preferences, Help
from PropEdit import PropertyEditors
from Companions import EventCollections
import Preferences, RTTI, Utils
from Preferences import IS, oiLineHeight, inspPageNames, flatTools
from Preferences import keyDefs

scrollBarWidth = 0
IECWidthFudge = 3

[wxID_ENTER, wxID_UNDOEDIT, wxID_CRSUP, wxID_CRSDOWN, wxID_CONTEXTHELP, 
 wxID_SWITCHDESIGNER, wxID_SWITCHEDITOR, wxID_OPENITEM, wxID_CLOSEITEM,
 wxID_INDEXHELP,
] = Utils.wxNewIds(10)

[wxID_INSPECTORFRAME, wxID_INSPECTORFRAMECONSTR, wxID_INSPECTORFRAMEEVENTS,
 wxID_INSPECTORFRAMEPAGES, wxID_INSPECTORFRAMEPROPS,
 wxID_INSPECTORFRAMESTATUSBAR, wxID_INSPECTORFRAMETOOLBAR,
] = map(lambda _init_ctrls: wxNewId(), range(7))

[wxID_INSPECTORFRAMETOOLBARTOOLS0] = map(lambda _init_coll_toolBar_Tools: wxNewId(), range(1))

class InspectorFrame(wxFrame, Utils.FrameRestorerMixin):
    """ Main Inspector frame, mainly does frame initialisation and handles
        events from the toolbar """
    _custom_classes = {'wxNotebook': ['InspectorNotebook'],
                       'wxScrolledWindow': ['InspectorPropScrollWin',
                                            'InspectorConstrScrollWin'],
                       'wxSplitterWindow': ['EventsWindow'] }
    def _init_coll_toolBar_Tools(self, parent):
        # generated method, don't edit

        parent.AddTool(bitmap=self.up_bmp, id=wxID_INSPECTORFRAMETOOLBARTOOLS0,
              isToggle=false, longHelpString='', pushedBitmap=wxNullBitmap,
              shortHelpString='Select parent')
        EVT_TOOL(self, wxID_INSPECTORFRAMETOOLBARTOOLS0, self.OnUp)

        parent.Realize()

    def _init_coll_statusBar_Fields(self, parent):
        # generated method, don't edit
        parent.SetFieldsCount(2)

        parent.SetStatusText('Nothing selected', 0)
        parent.SetStatusText('', 1)

        parent.SetStatusWidths([-1, -1])

    def _init_coll_pages_Pages(self, parent):
        # generated method, don't edit

        parent.AddPage(select=true, imageId=-1, page=self.constr,
              text=self.constr_name)
        parent.AddPage(select=false, imageId=-1, page=self.props,
              text=self.props_name)
        parent.AddPage(select=false, imageId=-1, page=self.events,
              text=self.events_name)

    def _init_utils(self):
        # generated method, don't edit
        self.paletteImages = wxImageList(height=24, width=24)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wxFrame.__init__(self, id=wxID_INSPECTORFRAME, name='', parent=prnt,
              pos=wxPoint(363, 272), size=wxSize(290, 505),
              style=wxDEFAULT_FRAME_STYLE | Preferences.childFrameStyle,
              title='Inspector')
        self._init_utils()
        self.SetClientSize(wxSize(282, 478))
        EVT_SIZE(self, self.OnSizing)
        EVT_CLOSE(self, self.OnCloseWindow)

        self.toolBar = wxToolBar(id=wxID_INSPECTORFRAMETOOLBAR, name='toolBar',
              parent=self, pos=wxPoint(0, 0), size=wxSize(282, 24),
              style=wxTB_HORIZONTAL | wxNO_BORDER | Preferences.flatTools | wxCLIP_CHILDREN)
        self._init_coll_toolBar_Tools(self.toolBar)
        self.SetToolBar(self.toolBar)

        self.statusBar = wxStatusBar(id=wxID_INSPECTORFRAMESTATUSBAR,
              name='statusBar', parent=self, style=wxST_SIZEGRIP)
        self.statusBar.SetFont(wxFont(Preferences.inspStatBarFontSize,
              wxDEFAULT, wxNORMAL, wxBOLD, false, ''))
        self.SetStatusBar(self.statusBar)

        self.pages = InspectorNotebook(id=wxID_INSPECTORFRAMEPAGES,
              name='pages', parent=self, pos=wxPoint(0, 24), size=wxSize(282,
              434), style=0)

        self.constr = InspectorConstrScrollWin(id=wxID_INSPECTORFRAMECONSTR,
              name='constr', parent=self.pages, pos=wxPoint(0, 0),
              size=wxSize(274, 408), style=wxSUNKEN_BORDER)

        self.props = InspectorPropScrollWin(id=wxID_INSPECTORFRAMEPROPS,
              name='props', parent=self.pages, pos=wxPoint(0, 0),
              size=wxSize(274, 408), style=wxSUNKEN_BORDER)

        self.events = EventsWindow(id=wxID_INSPECTORFRAMEEVENTS, name='events',
              parent=self.pages, point=wxPoint(0, 0), size=wxSize(274, 404),
              style=wxSP_3D)

        self._init_coll_pages_Pages(self.pages)

    def __init__(self, parent):
        self.constr_name = Preferences.inspPageNames['Constr']
        self.props_name = Preferences.inspPageNames['Props']
        self.events_name = Preferences.inspPageNames['Evts']

        self.up_bmp = IS.load('Images/Inspector/Up.png')
        self._init_ctrls(parent)
        del self.up_bmp

        # moved generated code down for wxPython 2.5 compatibility.
        self._init_coll_statusBar_Fields(self.statusBar)
        
        # Inspector is created before the Editor so this must be set after
        # creating the Editor
        self.editor = None

        self.winConfOption = 'inspector'
        self.loadDims()

        self.propertyRegistry = PropertyEditors.PropertyRegistry()
        PropertyEditors.registerEditors(self.propertyRegistry)

        self.destroying = false

        for cmpInf in PaletteStore.compInfo.values():
            filename ='Images/Palette/'+ cmpInf[0]+'.png'
            if IS.canLoad(filename):
            #if os.path.exists(Preferences.pyPath+'/'+filename):
                cmpInf.append(self.paletteImages.Add(IS.load(filename)))
            else:
                cmpInf.append(self.paletteImages.Add(IS.load('Images/Palette/Component.png')))

        self.SetIcon(IS.load('Images/Icons/Inspector.ico'))

        self.vetoSelect = false
        self.selObj = None
        self.selCmp = None
        self.selDesgn = None
        self.prevDesigner = (None, None)
        self.prevCollDesgn = None
        self.sessionHandler = None

        self.toolBar.AddSeparator()
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/Delete.png', 'Delete selection', self.OnDelete)
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/Cut.png', 'Cut selection', self.OnCut)
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/Copy.png', 'Copy selection', self.OnCopy)
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/Paste.png', 'Paste selection', self.OnPaste)
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Editor/Refresh.png', 'Recreate selection', self.OnRecreateSelection)
        self.toolBar.AddSeparator()
        self.wxID_POST = Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Inspector/Post.png', 'Post the session', self.OnPost)
        self.wxID_CANCEL = Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Inspector/Cancel.png', 'Cancel the session', self.OnCancel)
        self.toolBar.AddSeparator()
##        Utils.AddToolButtonBmpIS(self, self.toolBar, 'Images/Shared/RevertItem.png',
##          'Revert item', self.OnRevertItem)
        self.wxID_ADDITEM = Utils.AddToolButtonBmpIS(self, self.toolBar,
              'Images/Shared/NewItem.png', 'New item', self.OnNewItem)
        self.wxID_DELITEM = Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/DeleteItem.png', 'Delete item', self.OnDelItem)
        self.toolBar.AddSeparator()
        Utils.AddToolButtonBmpIS(self, self.toolBar,
          'Images/Shared/Help.png', 'Show help', self.OnHelp)
        self.toolBar.Realize()

        self.constr.setInspector(self)
        self.props.setInspector(self)
        self.events.setInspector(self)

        if wxPlatform == '__WXGTK__':
            prxy, self.containment = Utils.wxProxyPanel(self.pages, ParentTree)
        else:
            prxy = self.containment = ParentTree(self.pages)
        self.containment.SetImageList(self.paletteImages)
        self.pages.AddPage(prxy, inspPageNames['Objs'])

        self.selection = None

        EVT_MENU(self, wxID_SWITCHEDITOR, self.OnSwitchEditor)
        EVT_MENU(self, wxID_SWITCHDESIGNER, self.OnSwitchDesigner)
        EVT_MENU(self, wxID_INDEXHELP, self.OnIndexHelp)
        self.SetAcceleratorTable(wxAcceleratorTable([\
          (keyDefs['Designer'][0], keyDefs['Designer'][1], wxID_SWITCHEDITOR),
          (keyDefs['Inspector'][0], keyDefs['Inspector'][1], wxID_SWITCHDESIGNER),
          (keyDefs['HelpFind'][0], keyDefs['HelpFind'][1], wxID_INDEXHELP)]
        ))

        self.updateToolBarState()

    def OnSwitchEditor(self, event):
        if self.editor:
            self.editor.restore()

    def OnSwitchDesigner(self, event):
        if self.selDesgn:
            self.selDesgn.restore()

    def setDefaultDimensions(self):
        self.SetDimensions(0, Preferences.underPalette,
                           Preferences.inspWidth, Preferences.bottomHeight)

#---Object selection------------------------------------------------------------
    def selectObject(self, compn, selectInContainment=true, collDesgn=None,
          focusPage=None, restore=false, sessionHandler=None):
        """ Select an object in the inspector by populating the property
            pages. This method is called from the InspectableObjectView
            derived classes """
        if restore:
            self.restore()

        if self.sessionHandler:
            self.sessionHandler.promptPostOrCancel(self)

        if focusPage is not None:
            if self.pages.GetSelection() != focusPage:
                self.pages.SetSelection(focusPage)

        if self.selCmp == compn or self.vetoSelect:
            return

        # Clear inspector selection
        self.constr.cleanup()
        self.props.cleanup()
        self.events.cleanup()

        if self.prevDesigner[0] and compn.designer and not collDesgn and \
          (compn.designer != self.prevDesigner[0] or not collDesgn and self.prevDesigner[1]):
            if compn.designer.supportsParentView:
                compn.designer.refreshContainment()

        # deselect last selection if in different designer
        if self.prevDesigner[0] and self.prevDesigner != (compn.designer, collDesgn):
            if self.prevDesigner[1]:
                self.prevDesigner[1].selectNone()
            else:
                self.prevDesigner[0].selectNone()

        self.prevDesigner = (compn.designer, collDesgn)

        self.selCmp = compn
        self.selDesgn = compn.designer
        self.selObj = compn.control
        self.sessionHandler = sessionHandler

        self.statusBar.SetStatusText(compn.name)
        self.statusBar.SetStatusText(compn.GetClass(), 1)
        # Update progress inbetween building of property pages
        # Is this convoluted or what :)
        if self.selDesgn:
            sb = self.selDesgn.model.editor.statusBar.progress
        else: sb = None

        if sb: sb.SetValue(10)

        try:
            c_p = compn.getPropList()
            if sb: sb.SetValue(30)
            self.constr.readObject(c_p['constructor'])
            if sb: sb.SetValue(50)
            self.props.readObject(c_p['properties'])
            if sb: sb.SetValue(70)
            self.events.readObject()
            if sb: sb.SetValue(90)
    
            if selectInContainment and self.containment.valid:
                # XXX Ugly must change
                try:
                    treeId = self.containment.treeItems[compn.name]
                except:
                    treeId = self.containment.treeItems['']
    
                self.containment.valid = false
                self.containment.SelectItem(treeId)
                self.containment.valid = true
                self.containment.EnsureVisible(treeId)
    
        finally:
            if sb: sb.SetValue(0)

        # set add item state
        self.updateToolBarState()

    def multiSelectObject(self, compn, designer):
        self.selCmp = compn
        self.selDesgn = designer
        self.selObj = None

    # These methods update property pages.
    # Call when changes in the selected control is detected
    def pageUpdate(self, page, name):
        nv = page.getNameValue(name)
        if nv:
            page.initFromComponent(name)
    def propertyUpdate(self, name):
        self.pageUpdate(self.props, name)
    def constructorUpdate(self, name):
        self.pageUpdate(self.constr, name)
    def eventUpdate(self, name, delete=false):
        if delete:
            self.events.definitions.removeEvent(name)
        else:
            self.pageUpdate(self.events, name)

    # Direct companion source update of position and size when multiselected
    # While multiple components are selected the inspector does not persist
    # selected control value changes
    def directPositionUpdate(self, comp):
        comp.persistProp('Position', 'SetPosition', `comp.control.GetPosition()`)
    def directSizeUpdate(self, comp):
        comp.persistProp('Size', 'SetSize', `comp.control.GetSize()`)

##    def selectedCtrlHelpFile(self):
##        """ Return the help file/link associated with the selected control """
##        if self.selCmp: return self.selCmp.wxDocs
##        else: return ''

    def cleanup(self):
##        if self.sessionHandler is not None:
##            self.sessionHandler.promptPostOrCancel()

        self.selCmp = None
        self.selObj = None
        self.selDesgn = None
        self.sessionHandler = None
        self.constr.cleanup()
        self.props.cleanup()
        self.events.cleanup()
        self.statusBar.SetStatusText('')
        self.statusBar.SetStatusText('', 1)

        self.updateToolBarState()

    def initSashes(self):
        self.constr.initSash()
        self.props.initSash()
        self.events.initSash()

    def updateToolBarState(self):
        canAddDel = self.selCmp is not None and \
              hasattr(self.selCmp, 'propItems') and \
              hasattr(self.selCmp, 'updateZopeProps')
        self.toolBar.EnableTool(self.wxID_ADDITEM, canAddDel)
        self.toolBar.EnableTool(self.wxID_DELITEM, canAddDel)

        hasSessionHandler = self.sessionHandler is not None
        self.toolBar.EnableTool(self.wxID_POST, hasSessionHandler)
        self.toolBar.EnableTool(self.wxID_CANCEL, hasSessionHandler)

    def OnSizing(self, event):
        event.Skip()

    def OnDelete(self, event):
        if self.selDesgn:
            self.selDesgn.OnControlDelete(event)

    def OnUp(self, event):
        if self.sessionHandler:
            self.sessionHandler.doUp(self)
        else:
            self.cleanup()

    def OnCut(self, event):
        if self.selDesgn:
            self.selDesgn.OnCutSelected(event)
    def OnCopy(self, event):
        if self.selDesgn:
            self.selDesgn.OnCopySelected(event)
    def OnPaste(self, event):
        if self.selDesgn:
            self.selDesgn.OnPasteSelected(event)
    def OnRecreateSelection(self, event):
        if self.selDesgn:
            self.selDesgn.OnRecreateSelected(event)

    def OnPost(self, event):
        if self.sessionHandler:
            self.sessionHandler.doPost(self)

    def OnCancel(self, event):
        if self.sessionHandler:
            self.sessionHandler.doCancel(self)

    def OnHelp(self, event):
        Help.showHelp('Inspector.html')

    def OnIndexHelp(self, event):
        self.editor.OnHelpFindIndex(event)

    def OnRevertItem(self, event):
        if self.selCmp and self.props.prevSel and self.props.prevSel.propEditor:
            propEdit = self.props.prevSel.propEditor
            propEdit.companion.propRevertToDefault(propEdit.name,
                  propEdit.propWrapper.getSetterName())
            self.props.prevSel.showPropNameModified()

    def refreshZopeProps(self):
        cmpn = self.selCmp
        cmpn.updateZopeProps()
        self.selCmp = None
        self.selectObject(cmpn)

    def OnNewItem(self, event):
        if self.selCmp and hasattr(self.selCmp, 'propItems'):
            from ZopeLib import PropDlg
            dlg = PropDlg.create(self)
            try:
                if dlg.ShowModal() == wxID_OK:
                    self.selCmp.addProperty(dlg.tcPropName.GetValue(),
                          dlg.tcValue.GetValue(), dlg.chType.GetStringSelection())
                    self.refreshZopeProps()
            finally:
                dlg.Destroy()
    def OnDelItem(self, event):
        if self.selCmp and self.props.prevSel and hasattr(self.selCmp, 'propItems'):
            self.selCmp.delProperty(self.props.prevSel.propName)
            self.refreshZopeProps()

    def OnCloseWindow(self, event):
        self.Show(false)
        if self.destroying or __name__ == '__main__':
            self.paletteImages = None
            self.cleanup()
            self.pages.destroy()
            self.constr.destroy()
            self.props.destroy()
            self.events.destroy()
            self.Destroy()
            event.Skip()
        elif Preferences.expandEditorOnCloseInspector:
            self.editor.expandOnInspectorClose()
    
    def restore(self):
        Utils.FrameRestorerMixin.restore(self)
        if Preferences.expandEditorOnCloseInspector:
            self.editor.restoreOnInspectorRestore()

           

wxID_PARENTTREE = wxNewId()
wxID_PARENTTREESELECTED = wxNewId()
class ParentTree(wxTreeCtrl):
    """ Specialised tree ctrl that displays parent child relationship of
        controls on the frame """
    # XXX Rather associate data with tree item than going only on the name
    def __init__(self, parent):
        wxTreeCtrl.__init__(self, parent, wxID_PARENTTREE, style = wxTR_HAS_BUTTONS | wxCLIP_CHILDREN | wxSUNKEN_BORDER)
        self.cleanup()
        EVT_TREE_SEL_CHANGED(self, wxID_PARENTTREE, self.OnSelect)

    def cleanup(self):
        self.designer = None
        self.valid = false
        self.treeItems = {}
        self.DeleteAllItems()
        self.root = None

    def addChildren(self, parent, dict, designer):
        """ Recursive method to construct parent/child relationships in a tree """
        for par in designer.objectOrder:
            if dict.has_key(par):
                img = PaletteStore.compInfo[designer.objects[par][1].__class__][2]
                itm = self.AppendItem(parent, par, img)
                self.treeItems[par] = itm
                if len(dict[par]):
                    self.addChildren(itm, dict[par], designer)
        self.Expand(parent)


    def refreshCtrl(self, root, relDict, designer):
        self.cleanup()
        self.designer = designer
        self.root = self.AddRoot(root,
         PaletteStore.compInfo[designer.objects[''][1].__class__.__bases__[0]][2])

        self.treeItems[''] = self.root
        self.addChildren(self.root, relDict[''], designer)

        self.valid = true

    def selectName(self, name):
        tii = wxTreeItemId()
        self.SelectItem(self.treeItems.get(name, tii))

    def selectedName(self):
        return self.GetItemText(self.GetSelection())

    def selectItemGUIOnly(self, name):
        tii = wxTreeItemId()
        self.SelectItem(self.treeItems.get(name, tii))

    def extendHelpUrl(self, wxClass, url):
        return wxClass, url

    def OnSelect(self, event=None):
        """ Event triggered when the selection changes in the tree """
        if self.valid:
            idx = self.GetSelection()
            if self.designer:
##                if idx == self.root:
##                if self.GetRootItem() == idx:
                # Ugly but nothing else works
                try:
                    ctrlInfo = self.designer.objects[self.GetItemText(idx)]
                except KeyError:
                    ctrlInfo = self.designer.objects['']

                if hasattr(self.designer, 'selection') and self.designer.selection:
                    self.designer.selection.selectCtrl(ctrlInfo[1], ctrlInfo[0])


class NameValue:
    """ Base class for all name value pairs that appear in the Inspector """
    def __init__(self, inspector, nameParent, valueParent, companion,
          rootCompanion, name, propWrapper, idx, indent,
          editor=None, options=None, names=None, ownerPropEdit=None):

        self.destr = false
        self.lastSizeN = 0
        self.lastSizeV = 0
        self.indent = indent
        self.inspector = inspector
        self.propName = name
        self.editing = false

        self.nameParent = nameParent
        self.valueParent = valueParent
        self.idx = idx
        self.nameBevelTop = None
        self.nameBevelBottom = None
        self.valueBevelTop = None
        self.valueBevelBottom = None

        lockEditor, attrName, self.isCat = self.checkLockedProperty(name,
              propWrapper.getSetterName(), companion)

        if lockEditor:
            editor = lockEditor
            self.locked = true
        else:
            self.locked = false

        if editor:
            self.propEditor = editor(name, valueParent, companion, rootCompanion,
              propWrapper, idx, valueParent.GetSize().x+IECWidthFudge, options,
              names)
        else:
            self.propEditor = self.inspector.inspector.propertyRegistry.factory(name,
              valueParent, companion, rootCompanion, propWrapper, idx,
              valueParent.GetSize().x + IECWidthFudge)

        # Hardwire locked properties to return frame attributes
        if lockEditor:
            self.propEditor.value = attrName

        self.expander = None
        if self.propEditor:
            self.propEditor.ownerPropEdit = ownerPropEdit
            self.updatePropValue()
            displayVal = self.propEditor.getDisplayValue()

            # check if it's expandable
            if PropertyEditors.esExpandable in self.propEditor.getStyle():
                mID = wxNewId()
                self.expander = wxCheckBox(nameParent, mID, '',
                  wxPoint(8 * self.indent, self.idx * oiLineHeight +2),
                  wxSize(13, 14))
                self.expander.SetValue(true)
                EVT_CHECKBOX(self.expander, mID, self.OnExpand)
        else:
            self.propValue = ''
            displayVal = ''

        # Create name and value controls and separators
        self.nameCtrl = wxGenStaticText(nameParent, -1, name,
          wxPoint(8 * self.indent + 16, idx * oiLineHeight +2),
          wxSize(inspector.panelNames.GetSize().x, oiLineHeight -3),
          style = wxCLIP_CHILDREN | wxST_NO_AUTORESIZE | wxNO_BORDER)
        self.nameCtrl.SetToolTipString(companion.getPropertyHelp(name))
        EVT_LEFT_DOWN(self.nameCtrl, self.OnSelect)

        self.showPropNameModified(self.isCat)

        self.value = wxStaticText(valueParent, -1, displayVal,
          wxPoint(2, idx * oiLineHeight +2), wxSize(inspector.getValueWidth(),
          oiLineHeight -3), style = wxCLIP_CHILDREN | wxST_NO_AUTORESIZE)
        self.value.SetForegroundColour(Preferences.propValueColour)
        self.value.SetToolTipString(displayVal)
        EVT_LEFT_DOWN(self.value, self.OnSelect)

        if lockEditor and not self.isCat:
            self.enboldenCtrl(self.value)

        sepCol = wxColour(160, 160, 160)

        self.separatorN = wxWindow(nameParent, -1, wxPoint(0,
          (idx +1) * oiLineHeight), wxSize(inspector.panelNames.GetSize().x, 1),
          style = wxCLIP_CHILDREN)
        self.separatorN.SetBackgroundColour(sepCol)

        self.separatorV = wxWindow(valueParent, -1, wxPoint(0,
          (idx +1) * oiLineHeight), wxSize(inspector.getValueWidth(), 1),
          style = wxCLIP_CHILDREN)
        self.separatorV.SetBackgroundColour(sepCol)

    def checkLockedProperty(self, name, setterName, companion):
        """ Determine if the property is locked """
        # XXX refactor, this is currently ugly
        try:
            srcVal = companion.persistedPropVal(name, setterName)
        except KeyError:
            pass
        else:
            if srcVal is not None:
                if srcVal == 'PROP_CATEGORY':
                    return PropertyEditors.LockedPropEdit, '', true

                if type(srcVal) is type([]):
                    if len(srcVal):
                        srcVal = srcVal[0]
                    else:
                        srcVal = ''
                if srcVal.startswith('self.') and \
                 hasattr(companion.designer.model.specialAttrs['self'], srcVal[5:]):
                    return PropertyEditors.LockedPropEdit, srcVal, false
        return None, '', false

    def destroy(self, cancel = false):
        self.hideEditor(cancel, noUpdate=true)
        self.destr = true
        self.nameCtrl.Destroy()
        self.value.Destroy()
        self.separatorN.Destroy()
        self.separatorV.Destroy()
        if self.expander:
            self.expander.Destroy()

    def createHelpUrl(self):
        if self.propEditor:
            pw = self.propEditor.propWrapper
            # custom help
            if pw.routeType == 'CompnRoute':
                return '', ''
            # wxWin help
            if pw.routeType == 'CtrlRoute':
                mthName = pw.getSetterName()
                mthObj = getattr(self.propEditor.companion.control, mthName)
                cls = mthObj.im_class.__name__
                if cls[-3:] == 'Ptr': cls = cls[:-3]
                return cls, cls + mthName
        return '', ''

    def updatePropValue(self):
        self.propValue = self.propEditor.getValue()

    def showPropNameModified(self, displayAsCat=false):
        if self.propEditor and Preferences.showModifiedProps:
            propEdit = self.propEditor
            propSetter = propEdit.propWrapper.getSetterName()
            mod = not propEdit.companion.propIsDefault(propEdit.name, propSetter)
            self.enboldenCtrl(self.nameCtrl, mod or displayAsCat)
            if displayAsCat:
                self.nameCtrl.SetForegroundColour(Preferences.propValueColour)


    def enboldenCtrl(self, ctrl, bold = true):
        fnt = ctrl.GetFont()
        ctrl.SetFont(wxFont(fnt.GetPointSize(),
          fnt.GetFamily(), fnt.GetStyle(), bold and wxBOLD or wxNORMAL,
          fnt.GetUnderlined(), fnt.GetFaceName()))

    def updateDisplayValue(self):
        dispVal = self.propEditor.getDisplayValue()
        currVal = self.value.GetLabel()
        if currVal != dispVal:
            self.value.SetLabel(dispVal)
            self.value.SetToolTipString(dispVal)
            self.showPropNameModified(self.isCat)

    def setPos(self, idx):
        self.idx = idx
        if self.expander:
            self.expander.SetPosition(wxPoint(8 * self.indent,
            self.idx * oiLineHeight + 2))
        self.nameCtrl.SetPosition(wxPoint(8 * self.indent + 16, idx * oiLineHeight +2))
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
                self.nameCtrl.SetSize(wxSize(nameWidth, self.nameCtrl.GetSize().y))
            else:
                self.nameCtrl.SetSize(wxSize(100, self.nameCtrl.GetSize().y))

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
        self.nameBevelTop = wxWindow(self.nameParent, -1,
          wxPoint(0, max(self.idx*oiLineHeight -1, 0)),
          wxSize(self.inspector.panelNames.GetSize().x, 1))
        self.nameBevelTop.SetBackgroundColour(wxBLACK)
        self.nameBevelBottom = wxWindow(self.nameParent, -1,
          wxPoint(0, (self.idx + 1)*oiLineHeight -1),
          wxSize(self.inspector.panelNames.GetSize().x, 1))
        self.nameBevelBottom.SetBackgroundColour(wxWHITE)
        if not self.locked and self.propEditor:
            self.value.SetLabel('')
            self.value.SetToolTipString('')
            self.value.SetSize((0, 0))
            self.propEditor.inspectorEdit()
        else:
            self.valueBevelTop = wxWindow(self.valueParent, -1,
              wxPoint(0, max(self.idx*oiLineHeight -1, 0)),
              wxSize(self.inspector.getValueWidth(), 1))
            self.valueBevelTop.SetBackgroundColour(wxBLACK)
            self.valueBevelBottom = wxWindow(self.valueParent, -1,
              wxPoint(0, (self.idx + 1)*oiLineHeight -1),
              wxSize(self.inspector.getValueWidth(), 1))
            self.valueBevelBottom.SetBackgroundColour(wxWHITE)
        self.editing = true

    def hideEditor(self, cancel=false, noUpdate=false):
        if self.propEditor:# and (not self.destr):
            if cancel:
                self.propEditor.inspectorCancel()
            else:
                if noUpdate:
                    # swallow exceptions as autoposted values can not be canceled
                    try: 
                        self.propEditor.inspectorPost()
                    except Exception, err:
                        wxLogError('Could not post %s because: %s: %s'%(
                              self.propName, err.__class__.__name__, str(err)))
                else:
                    self.propEditor.inspectorPost()
                    self.updateDisplayValue()
                    self.value.SetSize(wxSize(self.separatorV.GetSize().x,
                                              oiLineHeight-3))

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

        self.editing = false

    def OnSelect(self, event=None):
        self.inspector.propertySelected(self)

    def OnExpand(self, event):
        if event.Checked(): self.inspector.collapse(self)
        else: self.inspector.expand(self)

class PropNameValue(NameValue):
    """ Name value for properties, usually Get/Set methods, but can also be
        routed to Companion methods """
    def initFromComponent(self):
        """ Update Inspector after possible change to underlying control """
        if self.propEditor:
            self.propEditor.initFromComponent()
            if not self.propEditor.editorCtrl:
                self.updateDisplayValue()
            self.propEditor.persistValue(self.propEditor.valueAsExpr())

class ConstrNameValue(NameValue):
    """ Name value for constructor parameters """
    def initFromComponent(self):
        """ Update Inspector after possible change to underlying control """
        if self.propEditor:
            self.propEditor.initFromComponent()
            if not self.propEditor.editorCtrl:
                self.updateDisplayValue()
    def showPropNameModified(self, isCat=false):
        pass

class EventNameValue(NameValue):
    """ Name value for event definitions """
    def initFromComponent(self):
        if self.propEditor:
            self.propEditor.initFromComponent()
            if not self.propEditor.editorCtrl:
                self.updateDisplayValue()

class ZopePropNameValue(NameValue):
    """ Name value for properties, usually Get/Set methods, but can also be
        routed to Companion methods """
    def initFromComponent(self):
        pass

class EventsWindow(wxSplitterWindow):
    """ Window that hosts event name values and event category selection """
    def __init__(self, *_args, **_kwargs):
        wxSplitterWindow.__init__(self, _kwargs['parent'], _kwargs['id'],
          style = Preferences.splitterStyle)

        self.categories = wxSplitterWindow(self, -1,
              style=wxNO_3D|wxSP_3D|wxSP_LIVE_UPDATE)
        self.definitions = InspectorEventScrollWin(self, -1,
              style=wxSUNKEN_BORDER|wxTAB_TRAVERSAL)

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

        self.selMacClass = -1

        self.categories.SetMinimumPaneSize(20)
        self.categories.SplitVertically(self.categoryClasses, self.categoryMacros)
        self.categories.SetSashPosition(80)

    def setInspector(self, inspector):
        self.inspector = inspector
        self.definitions.setInspector(inspector)

    def readObject(self):
        #clean up all previous items
        self.cleanup()

        # List available categories
        for catCls in self.inspector.selCmp.events():
            self.categoryClasses.InsertStringItem(0, catCls)

        self.definitions.readObject()

        self.definitions.refreshSplitter()

    def cleanup(self):
        self.definitions.cleanup()
        self.categoryClasses.DeleteAllItems()
        self.categoryMacros.DeleteAllItems()

    def destroy(self):
        self.definitions.destroy()
        self.inspector = None

    def findMacro(self, name):
        for macro in EventCollections.EventCategories[\
              self.categoryClasses.GetItemText(self.selCatClass)]:
            if macro == name: return macro
        raise 'Macro: '+name+' not found.'

    def addEvent(self, name, value, wid = None):
        self.inspector.selCmp.persistEvt(name, value, wid)
        self.inspector.selCmp.evtSetter(name, value)

        self.definitions.addEvent(name)
        self.definitions.refreshSplitter()

    def getEvent(self, name):
        return self.definitions.getNameValue(name)

    def macroNameToEvtName(self, macName):
        flds = macName.split('_')
        del flds[0] #remove 'EVT'
        cmpName = self.inspector.selCmp.evtName()
        evtName = 'On'+cmpName[0].upper()+cmpName[1:]
        for fld in flds:
            evtName = evtName + fld.capitalize()
        return evtName

    def extendHelpUrl(self, wxClass, url):
        return wxClass, url

    def initSash(self):
        self.definitions.initSash()
        self.categories.SetSashPosition(80)
        self.SetSashPosition(Preferences.oiEventSelectionHeight)

    def OnCatClassSelect(self, event):
        self.selCatClass = event.m_itemIndex
        catClass = EventCollections.EventCategories[\
              self.categoryClasses.GetItemText(self.selCatClass)]
        for catMac in catClass:
            self.categoryMacros.InsertStringItem(0, catMac)

    def OnCatClassDeselect(self, event):
        self.selCatClass = -1
        self.selMacClass = -1
        self.categoryMacros.DeleteAllItems()

    def OnMacClassSelect(self, event):
        self.selMacClass = event.m_itemIndex

    def OnMacClassDeselect(self, event):
        self.selMacClass = -1

    def doAddEvent(self, catClassName, macName):
        companion = self.inspector.selCmp
        methName = self.macroNameToEvtName(macName)
        frameName = companion.designer.GetName()
        if catClassName in EventCollections.commandCategories:
            wid = companion.getWinId()
        else:
            wid = None
        nv = self.getEvent(macName)
        if nv:
            self.addEvent(macName, methName, wid)
            nv.initFromComponent()
            nv.OnSelect()

        else: self.addEvent(macName, methName, wid)


    def OnMacroSelect(self, event):
        if self.selMacClass > -1:
            catClassName = self.categoryClasses.GetItemText(self.selCatClass)
            macName = self.categoryMacros.GetItemText(self.selMacClass)

            self.doAddEvent(catClassName, macName)

##    def OnAdd(self, event):
##        self.OnMacroSelect(event)
##
##    def OnDelete(self, event):
##        if self.selMacClass > -1:
##            macName = self.categoryMacros.GetItemText(self.selMacClass)
##            self.addEvent(macName[4:], methName)

# When a namevalue in the inspector is clicked (selected) the following happens
# * Active property editor is hidden, data posted, controls freed
# * New namevalue's propertyeditor creates an editor

class NameValueEditorScrollWin(wxScrolledWindow):
    """ Window that hosts a list of name values. Also provides capability to
        scroll a line at a time, depending on the size of the list """

    def __init__(self, parent, id=-1, pos=wxDefaultPosition, size=wxDefaultSize,
                style=wxHSCROLL | wxVSCROLL, name='scrolledWindow'):
        wxScrolledWindow.__init__(self, parent, id,
                style=style)# | wxTAB_TRAVERSAL)
        self.nameValues = []
        self.prevSel = None
        self.splitter = wxSplitterWindow(self, -1, wxPoint(0, 0),
          parent.GetSize(), style = Preferences.splitterStyle | wxSP_3D)

        self.panelNames = wxPanel(self.splitter, -1,
          wxDefaultPosition, wxSize(100, 1), style=0)#wxTAB_TRAVERSAL)
        EVT_SIZE(self.panelNames, self.OnNameSize)
        self.panelValues = wxPanel(self.splitter, -1, style=0)
        EVT_SIZE(self.panelValues, self.OnNameSize)

        self.splitter.SplitVertically(self.panelNames, self.panelValues)
        self.splitter.SetSashPosition(100)
        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SetSashSize(4)

        EVT_SIZE(self, self.OnSize)

    def cleanup(self):
        self.prevSel = None
        # first post any open editor
        for i in self.nameValues:
            i.hideEditor(false, noUpdate=true)
        # then clean up
        for i in self.nameValues:
            i.destroy(true)

        self.nameValues = []
        self.refreshSplitter()

    def getNameValue(self, name):
        for nv in self.nameValues:
            if nv.propName == name:
                return nv
        return None

    def getWidth(self):
        return self.GetSize().x

    def getHeight(self):
        return len(self.nameValues) *oiLineHeight + 5

    def getValueWidth(self):
        return self.panelValues.GetClientSize().x + IECWidthFudge

    def refreshSplitter(self):
        s = wxSize(self.GetClientSize().x, self.getHeight())
        wOffset, hOffset = self.GetViewStart()
        puw, puh = self.GetScrollPixelsPerUnit()
        if hOffset and len(self.nameValues) < s.y /hOffset:
            hOffset = 0
        self.splitter.SetDimensions(wOffset * puw, hOffset * puh * -1, s.x, s.y)
        self.updateScrollbars(wOffset, hOffset)

    def updateScrollbars(self, wOffset, hOffset):
        height = len(self.nameValues)
        self.SetScrollbars(oiLineHeight, oiLineHeight, 0, height + 1, wOffset, hOffset) #height + 1

    def propertySelected(self, nameValue):
        """ Called when a new name value is selected """
        if self.prevSel:
            if nameValue == self.prevSel: return
            self.prevSel.hideEditor()
        nameValue.showEdit()
        self.prevSel = nameValue

    def resizeNames(self):
        for nv in self.nameValues:
            nv.resize(self.panelNames.GetSize().x, self.getValueWidth())

    def initSash(self):
        self.splitter.SetSashPosition(int(self.GetSize().x / 2.25))

    def getSubItems(self, nameValue):
        idx = nameValue.idx + 1
        idnt = nameValue.indent + 1
        res = []
        while 1:
            if idx >= len(self.nameValues): break
            nameValue = self.nameValues[idx]
            if nameValue.indent < idnt: break
            res.append(nameValue)
            idx = idx + 1
        return res

    def initFromComponent(self, name):
        """ Update a property and it's sub properies from the underlying
            control """

        nv = self.getNameValue(name)
        if nv:
            nv.initFromComponent()
            for nv in self.getSubItems(nv):
                nv.propEditor.companion.updateObjFromOwner()
                nv.propEditor.propWrapper.connect(nv.propEditor.companion.obj, nv.propEditor.companion)
                nv.initFromComponent()

    def OnSize(self, event):
        self.refreshSplitter()
        event.Skip()

    def OnNameSize(self, event):
        self.resizeNames()
        event.Skip()

class InspectorScrollWin(NameValueEditorScrollWin):
    """ Derivative of NameValueEditorScrollWin that adds knowledge about the
        Inspector and implements keyboard events """
    def __init__(self, parent, id=-1, pos=wxDefaultPosition, size=wxDefaultSize,
                 style=wxHSCROLL | wxVSCROLL, name='scrolledWindow'):
        NameValueEditorScrollWin.__init__(self, parent, id, pos, size, style, name)

        self.EnableScrolling(false, true)

        self.selObj = None
        self.selCmp = None

        self.prevSel = None

        EVT_MENU(self, wxID_ENTER, self.OnEnter)
        EVT_MENU(self, wxID_UNDOEDIT, self.OnUndo)
        EVT_MENU(self, wxID_CRSUP, self.OnCrsUp)
        EVT_MENU(self, wxID_CRSDOWN, self.OnCrsDown)
        EVT_MENU(self, wxID_CONTEXTHELP, self.OnContextHelp)
        EVT_MENU(self, wxID_OPENITEM, self.OnOpenItem)
        EVT_MENU(self, wxID_CLOSEITEM, self.OnCloseItem)

        self.SetAcceleratorTable(wxAcceleratorTable([\
          (0, WXK_RETURN, wxID_ENTER),
          (0, WXK_ESCAPE, wxID_UNDOEDIT),
          (keyDefs['ContextHelp'][0], keyDefs['ContextHelp'][1], wxID_CONTEXTHELP),
          (0, WXK_UP, wxID_CRSUP),
          (0, WXK_DOWN, wxID_CRSDOWN),
          (wxACCEL_CTRL, WXK_RIGHT, wxID_OPENITEM),
          (wxACCEL_CTRL, WXK_LEFT, wxID_CLOSEITEM),
          ]))

    def setInspector(self, inspector):
        self.inspector = inspector
        self.selObj = inspector.selObj
        self.selCmp = inspector.selCmp

    def destroy(self):
        self.inspector = None

    def readObject(self, propList):
        """ Override this method in derived classes to implement the
            initialisation and construction of the name value list """

    def findEditingNameValue(self):
        for idx in range(len(self.nameValues)):
            if self.nameValues[idx].editing:
                return idx
        return -1

    def deleteNameValues(self, idx, count, cancel = false):
        """ Removes a range of name values from the Inspector.
            Used to collapse sub properties
        """
        deleted = 0
        if idx < len(self.nameValues):
            # delete sub properties
            while (idx < len(self.nameValues)) and (deleted < count):
                if self.nameValues[idx] == self.prevSel: self.prevSel = None
                self.nameValues[idx].destroy(cancel)
                del self.nameValues[idx]
                deleted = deleted + 1

            # move properties up
            for idx in range(idx, len(self.nameValues)):
                self.nameValues[idx].setPos(idx)

    def extendHelpUrl(self, wxClass, url):
        return wxClass, url

    def collapse(self, nameValue):
        # delete all NameValues until the same indent, count them
        startIndent = nameValue.indent
        idx = nameValue.idx + 1

        # Move deletion into method and use in removeEvent of EventWindow
        i = idx
        if i < len(self.nameValues):
            while (i < len(self.nameValues)) and \
              (self.nameValues[i].indent > startIndent):
                i = i + 1
        count = i - idx

        self.deleteNameValues(idx, count)
        self.refreshSplitter()
        nameValue.propEditor.expanded = false

    def OnEnter(self, event):
        for nv in self.nameValues:
            if nv.editing:
                try:
                    nv.propEditor.inspectorPost(false)
                except Exception, err:
                    wxMessageBox('%s: %s'%(err.__class__, str(err)), 
                          'Unable to post, please correct.', 
                          wxOK | wxCENTER | wxICON_ERROR, self)

    def OnUndo(self, event):
        # XXX Implement!
        pass

    def OnCrsUp(self, event):
        if len(self.nameValues) > 1:
            for idx in range(1, len(self.nameValues)):
                if self.nameValues[idx].editing:
                    self.propertySelected(self.nameValues[idx-1])
                    break
            else:
                self.propertySelected(self.nameValues[0])

            x, y = self.GetViewStart()
            if y >= idx:
                self.Scroll(x, y-1)

    def OnCrsDown(self, event):
        if len(self.nameValues) > 1:
            for idx in range(len(self.nameValues)-1):
                if self.nameValues[idx].editing:
                    self.propertySelected(self.nameValues[idx+1])
                    break
            else:
                self.propertySelected(self.nameValues[-1])

            dx, dy = self.GetScrollPixelsPerUnit()
            cs = self.GetClientSize()
            x, y = self.GetViewStart()
            if y <= idx + 1 - cs.y / dy:
                self.Scroll(x, y+1)

    def OnContextHelp(self, event):
        if self.inspector.selCmp:
            wxClass, url = self.extendHelpUrl(self.inspector.selCmp.GetClass(), '')
            if wxClass:
                Help.showCtrlHelp(wxClass, url)

    def OnOpenItem(self, event):
        idx = self.findEditingNameValue()
        if idx != -1:
            nameValue = self.nameValues[idx]
            if nameValue.expander and not nameValue.propEditor.expanded:
                self.expand(nameValue)
                nameValue.expander.SetValue(false)

    def OnCloseItem(self, event):
        idx = self.findEditingNameValue()
        if idx != -1:
            nameValue = self.nameValues[idx]
            if nameValue.expander and nameValue.propEditor.expanded:
                self.collapse(nameValue)
                nameValue.expander.SetValue(true)

class InspectorPropScrollWin(InspectorScrollWin):
    """ Specialised InspectorScrollWin that understands properties """
    def setNameValues(self, compn, rootCompn, nameValues, insIdx, indent, ownerPropEdit = None):
        top = insIdx
        # Add NameValues to panel
        for nameValue in nameValues:
            # Check if there is an associated companion
            if compn:
                self.nameValues.insert(top, PropNameValue(self, self.panelNames,
                  self.panelValues, compn, rootCompn, nameValue.name,
                  nameValue, top, indent,
                  compn.getPropEditor(nameValue.name),
                  compn.getPropOptions(nameValue.name),
                  compn.getPropNames(nameValue.name),
                  ownerPropEdit))
            top = top + 1

        self.refreshSplitter()

    def extendHelpUrl(self, wxClass, url):
        if self.prevSel:
            return self.prevSel.createHelpUrl()
        return wxClass, url

    # read in the root object
    def readObject(self, propList):
        self.setNameValues(self.inspector.selCmp, self.inspector.selCmp,
          propList, 0, 0)

    def expand(self, nameValue):
        nv = self.nameValues[nameValue.idx]
        obj = nv.propValue
        compn = nv.propEditor.getSubCompanion()\
            (nameValue.propName, self.inspector.selCmp.designer,
             self.inspector.selCmp, obj, nv.propEditor.propWrapper)

        compn.updateObjFromOwner()
#                nv.propEditor.propWrapper.connect(nv.propEditor.companion.obj, nv.propEditor.companion)
        propLst = compn.getPropList()['properties']
        sze = len(propLst)

        indt = self.nameValues[nameValue.idx].indent + 1

        # move properties down
        startIdx = nameValue.idx + 1
        for idx in range(startIdx, len(self.nameValues)):
            self.nameValues[idx].setPos(idx +sze)

        # add sub properties in the gap
        self.setNameValues(compn, self.inspector.selCmp, propLst, startIdx, indt, nv.propEditor)
        nv.propEditor.expanded = true
        nv.updateDisplayValue()

class InspectorConstrScrollWin(InspectorScrollWin):
    """ Specialised InspectorScrollWin that understands contructor parameters """
    def extendHelpUrl(self, wxClass, url):
        return wxClass, wxClass + url + 'constr'
    # read in the root object
    def readObject(self, constrList):
        params = self.inspector.selCmp.constructor()
        paramNames = params.keys() + self.inspector.selCmp.extraConstrProps().keys()

        paramNames.sort()

        compn = self.inspector.selCmp
        self.addParams(constrList, paramNames, compn, compn)

        self.refreshSplitter()

    def addParams(self, constrList, paramNames, compn, rootCompn, indent = 0, insIdx = -1):
        def findInConstrLst(name, constrList):
            for constr in constrList:
                if constr.name == name:
                    return constr
            return None
        for param in paramNames:
            propWrap = findInConstrLst(param, constrList)
            if propWrap:
                self.addProp(param, compn, rootCompn, propWrap, indent)
            else:
                self.addConstr(param, compn, rootCompn, indent)

    def expand(self, nameValue):
        nv = self.nameValues[nameValue.idx]
        obj = nv.propValue
        compn = nv.propEditor.getSubCompanion()\
            (nameValue.propName, self.inspector.selCmp.designer,
             self.inspector.selCmp, obj, nv.propEditor.propWrapper)

        propLst = compn.getPropList()['properties']
        sze = len(propLst)

        indt = self.nameValues[nameValue.idx].indent + 1

        # move properties down
        startIdx = nameValue.idx + 1
        for idx in range(startIdx, len(self.nameValues)):
            self.nameValues[idx].setPos(idx +sze)

        # add sub properties in the gap
        for propWrap in propLst:
            if propWrap:
                self.addProp(propWrap.name, compn, self.inspector.selCmp,
                      propWrap, indt, startIdx, nv.propEditor)
                startIdx = startIdx + 1
        nv.propEditor.expanded = true
        nv.updateDisplayValue()
        self.refreshSplitter()

    def addConstr(self, name, compn, rootCompn, indent = 0, insIdx = -1):
        props = compn.properties()
        if props.has_key(name):
            rType, getter, setter = props[name]
            propWrap = RTTI.PropertyWrapper(name, rType, getter, setter)
        else:
            propWrap = RTTI.PropertyWrapper(name, 'NoneRoute', None, None)

        if insIdx == -1:
            insIdx = len(self.nameValues)
        self.nameValues.insert(insIdx, ConstrNameValue(self, self.panelNames,
          self.panelValues, compn, rootCompn, name, propWrap,
          insIdx, indent,
          compn.getPropEditor(name), compn.getPropOptions(name),
          compn.getPropNames(name)))

    def addProp(self, name, compn, rootCompn, propWrap, indent = 0, insIdx = -1, ownerPropEdit = None):
        if insIdx == -1:
            insIdx = len(self.nameValues)
        self.nameValues.insert(insIdx,
          PropNameValue(self, self.panelNames, self.panelValues,
          compn, rootCompn, name, propWrap, insIdx, indent,
          compn.getPropEditor(name),
          compn.getPropOptions(name),
          compn.getPropNames(name),
          ownerPropEdit))

class InspectorEventScrollWin(InspectorScrollWin):
    """ Specialised InspectorScrollWin that understands events """
    def readObject(self):

        for evt in self.inspector.selCmp.getEvents():
            self.addEvent(evt.event_name)

        height = len(self.nameValues)
        self.refreshSplitter()

    def addEvent(self, name):
        nv = self.getNameValue(name)
        if nv: nv.initFromComponent()
        else:
            self.nameValues.insert(len(self.nameValues),
              EventNameValue(self, self.panelNames,
              self.panelValues, self.inspector.selCmp, self.inspector.selCmp,
              name, RTTI.PropertyWrapper(name, 'EventRoute',
              self.inspector.selCmp.evtGetter, self.inspector.selCmp.evtSetter),
              len(self.nameValues), -2, PropertyEditors.EventPropEdit))

        self.refreshSplitter()
    def removeEvent(self, name):
        # This event will always be selected by a property editor in edit mode
        # therefor nothing will be selected after this

        nv = self.getNameValue(name)
        self.deleteNameValues(nv.idx, 1, true)
        self.prevSel = None

class InspectorNotebook(wxNotebook):
    """ Notebook that hosts Inspector pages """
    def __init__(self, *_args, **_kwargs):
        wxNotebook.__init__(self, _kwargs['parent'], _kwargs['id'],
            style = Preferences.inspNotebookFlags)
        self.pages = {}
        self.inspector = _kwargs['parent']

    def destroy(self):
        self.pages = None
        self.inspector = None

    def AddPage(self, page, text, select=false, imageId=-1):
        wxNotebook.AddPage(self, page, text)
        self.pages[text] = page

    def extendHelpUrl(self, cls):
        return self.pages[self.GetPageText(self.GetSelection())].extendHelpUrl(cls, '')


if __name__ == '__main__':
    app = wxPySimpleApp()
    wxInitAllImageHandlers()
    frame = InspectorFrame(None)
    frame.Show(true)
    frame.initSashes()
    app.MainLoop()
