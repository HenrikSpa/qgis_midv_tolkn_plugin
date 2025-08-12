# -*- coding: utf-8 -*-
"""
/***************************************************************************
 This is the main part of the midv_tolkn plugin. 
 Mainly controlling user interaction and calling for other classes. 
                             -------------------
        begin                : 2016-07-30
        copyright            : (C) 2016 by Josef Källgården
        email                : groundwatergis [at] gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import datetime
# Import some general python modules
import os.path
import sys
import zipfile

import qgis.utils
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QFile
from qgis.PyQt.QtGui import QCursor, QIcon
from qgis.PyQt.QtWidgets import QAction, QApplication, QFileDialog, QMenu

try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

from qgis.utils import spatialite_connect
#add midv_tolkn plugin directory to pythonpath (needed here to allow importing modules from subfolders)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/tools'))

# Import midv_tolkn tools and modules
from .load_tolkn_layers import LoadLayers
from . import midv_tolkn_utils as utils 

class midv_tolkn:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(QFile.decodeName(__file__))
        self.db = None
        
    def initGui(self):
        # Create actions
        icon = QIcon(os.path.join(self.plugin_dir, "icons", "midv_tolkn.png"))
        
        self.actionloadthelayers = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'load_layers_domains.png')), "Ladda tolkningslager t QGIS", self.iface.mainWindow())
        self.actionloadthelayers.setWhatsThis("Laddar tolkningslager för gvmagasin m.m. till QGIS")
        self.actionloadthelayers.triggered.connect(lambda x: self.load_the_layers())

        self.actionNewDB = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'create_new.png')), "Skapa en ny tolkningsdatabas", self.iface.mainWindow())
        self.actionNewDB.triggered.connect(lambda x: self.new_db())

        self.actionVacuumDB = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'vacuum.png')), "Packa (vacuum) tolkn-db", self.iface.mainWindow())
        self.actionVacuumDB.setWhatsThis("Perform database vacuuming")
        self.actionVacuumDB.triggered.connect(lambda x: self.vacuum_db())

        self.actionZipDB = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'zip.png')), "Backup av tolknings-databas", self.iface.mainWindow())
        self.actionZipDB.setWhatsThis("En komprimerad zip-fil kommer att skapas i samma dir som tolknings-databasen.")
        self.actionZipDB.triggered.connect(lambda x: self.zip_db())

        self.actionUpgradeDB = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'create_new.png')), "Uppgradera tolknings-databas", self.iface.mainWindow())
        self.actionUpgradeDB.setWhatsThis("Uppgradera en befintlig tolknings-databas till ny databas-struktur.")
        self.actionUpgradeDB.triggered.connect(lambda x: self.upgrade_db())

        self.action_recalculate_tillromr = QAction(QIcon(os.path.join(self.plugin_dir, 'icons', 'create_new.png')), "Beräkna kolumner i tillromr på nytt", self.iface.mainWindow())
        self.action_recalculate_tillromr.setWhatsThis("Beräknar kolumnen area_km2, flode_lPs och dagvatten_lPs i lagret tillromr.")
        self.action_recalculate_tillromr.triggered.connect(lambda x: self.recalculate_tillromr())


        #self.actionabout = QAction(QIcon(":/plugins/midv_tolkn/icons/about.png"), "Information", self.iface.mainWindow())
        #self.actionabout.triggered.connect(lambda x: self.about)
        
        # Add button
        self.iface.addToolBarIcon(self.actionloadthelayers)
        
        # Add plugins menu items
        self.midv_menu = None # Midvatten-plugin-menyn
        self.menu = None # sub-menyn "Tolkningar"
        
        # Check if Midvatten-menyn existerar och get it
        for child in self.iface.mainWindow().menuBar().children(): 
            if isinstance(child,QMenu): 
                if child.title() == "Midvatten": # Put here your menu name
                    self.midv_menu = child

        # If the Midvatten menu does not exist, create it!
        self.owns_midv_menu = False #indicator that this plugin must not clean up the midvatten menu
        if not self.midv_menu:
            self.owns_midv_menu = True #indicator that this plugin must clean up the midvatten menu
            self.midv_menu = QMenu( "Midvatten", self.iface.mainWindow().menuBar() )
            menuBar = self.iface.mainWindow().menuBar()
            menuBar.addMenu(self.midv_menu)

        # check if there is a sub-menu Tolkningar
        for childchild in self.midv_menu.children(): 
            if isinstance(childchild,QMenu): 
                if childchild.title() == "&Tolkningar": # Put here your menu name
                    print('found sub-menu Tolkningar')
                    self.menu = childchild

        # If the tolkning submenu does not exist, create it
        if not self.menu:
            print('will add Tolkningar submenu')
            self.menu_separator1 = self.midv_menu.addSeparator()
            self.menu = QMenu(QCoreApplication.translate("Midvatten", "&Tolkningar"))
            self.midv_menu.addMenu(self.menu)
            self.menu_separator2 = self.midv_menu.addSeparator()
            
        self.menu.addAction(self.actionloadthelayers)   
        self.menu.addAction(self.actionNewDB)   
        self.menu.addAction(self.actionVacuumDB)
        self.menu.addAction(self.actionZipDB)
        self.menu.addAction(self.actionUpgradeDB)
        self.menu.addAction(self.action_recalculate_tillromr)
        #self.menu.addAction(self.actionabout)

    def unload(self):    
        # remove tool bar button
        self.iface.removeToolBarIcon(self.actionloadthelayers)

        # Remove the plugin menu items and icons
        try:
                self.midv_menu.removeAction(self.menu.menuAction())
                self.midv_menu.removeAction(self.menu_separator1)
                self.midv_menu.removeAction(self.menu_separator2)
        except:
                pass
        if self.owns_midv_menu: #indicator that this plugin must clean up the midvatten menu
            menubar = self.midv_menu.parentWidget()
            menubar.removeAction(self.midv_menu.menuAction())
            self.midv_menu.deleteLater()

    def about(self):   
        utils.pop_up_info(msg='This feature is not yet implemented',title='Hold on...')

    def load_data_domains(self):
        #utils.pop_up_info(msg='This feature is not yet implemented',title='Hold on...')
        #return
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        err_flag = utils.verify_msettings_loaded_and_layer_edit_mode(qgis.utils.iface, self.ms)#verify midv settings are loaded
        if err_flag == 0:
            conn_ok, dd_tables = utils.sql_load_fr_db("select name from sqlite_master where name like 'zz_%'")
            if not conn_ok:
                return
            d_domain_tables = [str(dd_table[0]) for dd_table in dd_tables]
            err_flag = utils.verify_msettings_loaded_and_layer_edit_mode(qgis.utils.iface, self.ms, d_domain_tables)#verify none of the tables are already loaded and in edit mode
            if err_flag == 0:
                LoadLayers(qgis.utils.iface, self.ms.settingsdict,'Midvatten_data_domains')
        QApplication.restoreOverrideCursor()#now this long process is done and the cursor is back as normal

    def load_the_layers(self):
        loadlayers = LoadLayers(qgis.utils.iface,self.db)
        self.db = loadlayers.dbpath

    def new_db(self, set_locale=False):
        if not set_locale:
            set_locale = utils.getcurrentlocale()

        filenamepath = os.path.join(os.path.dirname(__file__),"metadata.txt" )
        iniText = QSettings(filenamepath , QSettings.IniFormat)
        verno = str(iniText.value('version')) 
        from .create_tolkn_db import NewDb
        newdbinstance = NewDb(self.iface, verno, set_locale=set_locale)
        if not newdbinstance.dbpath=='':
            self.db = newdbinstance.dbpath

    def upgrade_db(self, set_locale=False):
        from_db = None
        #get full path to the original db to be updated
        if self.db:
            use_current_db = utils.Askuser("YesNo","""Do you want to upgrade %s?"""%self.db,'Current database?')
            if use_current_db.result == 0:
                from_db = None
            elif use_current_db.result == 1:
                from_db = self.db
            elif use_current_db.result == '':
                return
        if not from_db:
            from_db = QFileDialog.getOpenFileName(None, 'Ange tolknings-db som ska exporteras','',"Spatialite (*.sqlite)")[0]
        if not from_db:
            QApplication.restoreOverrideCursor()
            return None

        #get EPSG in the original db
        EPSG = utils.sql_load_fr_db("""SELECT srid FROM geom_cols_ref_sys WHERE Lower(f_table_name) = Lower('gvmag') AND Lower(f_geometry_column) = Lower('geometry')""", from_db)

        #preparations to create new db of new design
        if not set_locale:
            set_locale = utils.getcurrentlocale()

        filenamepath = os.path.join(os.path.dirname(__file__),"metadata.txt" )
        iniText = QSettings(filenamepath , QSettings.IniFormat)
        verno = str(iniText.value('version'))

        #now create database of the updated design
        from .create_tolkn_db import NewDb
        newdbinstance = NewDb(self.iface, verno, user_select_CRS=True, EPSG_code=EPSG[1][0][0], set_locale=set_locale)
        if not newdbinstance.dbpath:
            QApplication.restoreOverrideCursor()
            return None
        #transfer data to the new database
        foo = utils.UpgradeDatabase(from_db, newdbinstance.dbpath)

        #set new database as the current db and load these layers
        if not newdbinstance.dbpath=='':
            self.db = newdbinstance.dbpath
        self.load_the_layers()

    def recalculate_tillromr(self):
        if not self.db:
            db, ok = QFileDialog.getOpenFileName(None,
                                                  'Ange tolknings-db',
                                                  '', "Spatialite (*.sqlite)")
            if not ok:
                return
        else:
            db = self.db
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for sql in utils.recalculate_tillromr_queries:
                utils.sql_alter_db(db, sql)
        except:
            QApplication.restoreOverrideCursor()
            raise
        else:
            QApplication.restoreOverrideCursor()
            self.iface.messageBar().pushSuccess("Information",
                                                "Columns area_km2, flode_lPs and dagvatten_lPs recalculated in table tillromr")
        
    def vacuum_db(self):
        force_another_db = False
        if self.db:
            use_current_db = utils.Askuser("YesNo","""Vill du packa %s?"""%self.db,'Which database?')
            if use_current_db.result == 1:
                dbpath = self.db
                force_another_db = True
            elif use_current_db.result == 0:
                force_another_db = True
            elif use_current_db.result == '':
                return
        if not self.db or force_another_db:
            dbpath = QFileDialog.getOpenFileName(None, 'Ange db som ska packas','',"Spatialite (*.sqlite)")[0]

        QApplication.setOverrideCursor(Qt.WaitCursor)
        utils.sql_alter_db(dbpath,'vacuum')
        QApplication.restoreOverrideCursor()
        
    def zip_db(self):
        force_another_db = False
        dbpath=None
        if self.db:
            use_current_db = utils.Askuser("YesNo",'Vill du göra backup av %s?'%self.db,'Which database?')
            if use_current_db.result == 1:
                dbpath = self.db
                force_another_db = False
            elif use_current_db.result == 0:
                force_another_db = True
            elif use_current_db.result == '':
                return
        if not self.db or force_another_db:
            dbpath = QFileDialog.getOpenFileName(None, 'Ange db som du vill skapa backup utav','',"Spatialite (*.sqlite)")[0]

        if dbpath:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            connection = utils.dbconnection(dbpath)
            connection.connect2db()
            connection.conn.cursor().execute("begin immediate")

            file_path = os.path.realpath(dbpath)
            dir_path = os.path.dirname(file_path)
            current_dir = dir_path.split(os.sep)[-1]

            bkupname = dbpath + datetime.datetime.now().strftime('%Y%m%dT%H%M') + '.zip'
            zf = zipfile.ZipFile(bkupname, mode='w')
            zf.write(dbpath,os.path.basename(dbpath), compress_type=compression) #compression will depend on if zlib is found or not
            zf.close()
            connection.conn.rollback()
            connection.closedb()
            self.iface.messageBar().pushSuccess("Information", "Database backup was written to " + bkupname)
            QApplication.restoreOverrideCursor()
