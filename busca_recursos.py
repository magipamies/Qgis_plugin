# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BuscaRecursos
                                 A QGIS plugin
 Buscador de recursos
                              -------------------
        begin                : 2019-04-11
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Magí Pàmies Sans
        email                : magipamies@gmail.com
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
from PyQt4.QtCore import (QSettings, QTranslator, qVersion, QCoreApplication,
                          QVariant)
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from busca_recursos_dialog import BuscaRecursosDialog
import os.path
import requests
from qgis.utils import iface
from qgis.gui import QgsMessageBar
import overpy
from qgis.core import (QgsVectorLayer, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsField, QgsMapLayerRegistry,
                       QgsPoint, QgsGeometry, QgsFeature)

# Indico les constants
AMENITIES = ("https://taginfo.openstreetmap.org/api/4/key/values?key=amenity&"
             "filter=nodes&lang=es&sortname=count&sortorder=desc&page=1&rp=50&"
             "qtype=value&format=json_pretty")

# Creo una funció per poder seleccionar la capa en funció del lloc i de la
# amenity
def selecciona_capa(lloc, amenity):
    """Retorna una capa amb format json."""
    api = overpy.Overpass()
    query = ('[out:json];'
             'area["name"="%s"]["admin_level"=8];'
             'node["amenity"="%s"](area);'
             'out;') % (lloc.capitalize(), amenity)
    capa = api.query(query)

    return capa


class BuscaRecursos:
    """QGIS Plugin Implementation."""



    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BuscaRecursos_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

            # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Buscador de recursos')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'BuscaRecursos')
        self.toolbar.setObjectName(u'BuscaRecursos')

        # Defineixo les varibles que necessitem hi estiguin quan s'intancia la
        # classe
        self.lloc = None
        self.tipus = None
        self.capa_objecte = None
        self.entitat = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BuscaRecursos', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = BuscaRecursosDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Valor per defecte de la variable distancia
        self.distancia = 0
        icon_path = ':/plugins/BuscaRecursos/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Buscador de recursos'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Quan l'usuari cliqui "Busca Lloc" executarà el mètode
        # self.obte_lloc
        self.dlg.busca_lloc.clicked.connect(self.obte_lloc)

        # Quan l'usuari cliqui "Busca tipus" executarà el mètode
        # self.obte_llista_tipus
        self.dlg.busca_tipus.clicked.connect(self.obte_llista_tipus)

        # Quan l'usuari modifiqui la selecció al box "tipus_selec" execturarà
        # el mètode sef.obte_tipus
        self.dlg.tipus_selec.activated.connect(self.obte_tipus)

        # Valida la distància quan s'Introdueix el valor
        self.dlg.distancia.valueChanged.connect(self.validar_distancia)

        # Quan l'usuari cliqui "Busca capa" executarà el mètode
        # self.obte_llista_capa_objecte
        self.dlg.busca_capa_objecte.clicked.connect(
            self.obte_llista_capa_objecte)

        # Quan l'usuari modifiqui la selecció al box "capa_objecte_list"
        # execturarà el mètode sef.obte_capa_objecte
        self.dlg.capa_objecte_list.activated.connect(self.obte_capa_objecte)

        # Quan l'usuari cliqui "Busca entitat" executarà el mètode
        # self.obte_llista_entitat
        self.dlg.busca_entitat.clicked.connect(self.obte_llista_entitat)

        # Quan l'usuari modifiqui la selecció al box "entitat_select"
        # execturarà el mètode sef.obte_entitat
        self.dlg.entitat_select.activated.connect(self.obte_entitat)

        # Quan l'usuari cliqui "Executa" executarà el mètode
        # self.busca_entitats
        self.dlg.executa.clicked.connect(self.busca_entitats)

        # Quan l'usuari clicqui "Neteja", el formulari tornarà al seu
        # estat inicial
        self.dlg.neteja.clicked.connect(self.neteja)

        # Quan l'usuari clicqui "Cancela", netejarà la finestra i la tancarà
        self.dlg.cancela.clicked.connect(self.neteja)
        self.dlg.cancela.clicked.connect(self.dlg.close)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Buscador de recursos'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work."""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass


    def obte_lloc(self):
        """Retorna un lloc a on acotar la busqueda."""
        # Comprova que hi ha text escrit a la casella del lloc al witdget
        # Si no hi ha cap text escrit envia un misstge d'error i para la funció
        if len(self.dlg.lloc.text()) == 0:
            iface.messageBar().pushMessage(
                u"Escriu un lloc on fer la cerca",
                level=QgsMessageBar.CRITICAL,
                duration=10
            )
            # Deixem els valors per defecte a la casella del witget i a la
            # variable self.lloc. Això ho fem per si la variable tenia un valor
            # d'una consulta anterior
            self.dlg.lloc_usat.setText("Escriu un lloc a on acotar la cerca")
            self.lloc = None
            # Atura la funció
            return

        # Dona valor a la variable lloc
        self.lloc = self.dlg.lloc.text().encode('utf-8').capitalize()
        # Canvia el text de la casella de lloc del witget
        self.dlg.lloc_usat.setText(self.lloc)
        # Imprimeix un missatge a la pantalla de python
        print ("Lloc escollit => %s" % self.lloc)


    def obte_llista_tipus(self):
        """Retorna una llista de tipus de recurs que s'ha de buscar."""
        # Deixem els valors de per defecte, per si hi ha els valors d'una
        # consulta anterior
        self.dlg.tipus_selec.clear()
        self.dlg.tipus_usat.setText("Selecciona un tipus de la llista")
        self.tipus = None

        # Comprovem que la variable "lloc" tinguí un valor
        if not self.lloc:
            iface.messageBar().pushMessage(
                u"Primer has de seleccionar el lloc on fer la cerca",
                level=QgsMessageBar.CRITICAL,
                duration=10
            )
            return

        # Donem valor a la variable tipus
        tipus = self.dlg.tipus.text().encode('utf-8')

        # Definim la variable "llista_amenities"
        llista_amenities = requests.get(AMENITIES)
        llista_amenities = llista_amenities.json()

        # Busquem tots els elements de la variable "llista_amenities" que
        # continguin el text de la variable "tipus". Cada element que trobem
        # l'afegim al element QComboBox (tipus_selec)
        for element in llista_amenities['data']:
            if element['value']:
                if tipus.lower() in (str(element['value'].encode('utf-8')).
                                     lower()):
                    self.dlg.tipus_selec.addItem(element['value'])

        print (u"Trobats %d tipus de recurs a buscar" % (
                                                self.dlg.tipus_selec.count()))
        # Si no trobem cap element, li diem que enviï un missatge d'error
        if self.dlg.tipus_selec.count() < 1:
            iface.messageBar().pushMessage(
                u"No hi ha cap tipus amb %s. Torna-ho a provar" % (tipus),
                level=QgsMessageBar.CRITICAL,
                duration=10
            )


    def obte_tipus(self):
        """Retorna el tipus de recurs que s'ha de buscar."""
        # Donem valor a la variable self.tipus.
        self.tipus = self.dlg.tipus_selec.currentText()
        # Escribim el valor de la variable self.tipus al witdget
        self.dlg.tipus_usat.setText(self.tipus)
        # Creem la capa de tipus de reucrs a buscar, amb les variables lloc i
        # tipus. Mitjançant la funció "selecciona_capa"
        self.capa_tipus = selecciona_capa(self.lloc, self.tipus)

        print(u"Comprovant si hi ha cap %s a %s" % (self.tipus, self.lloc))
        # Comprova si hi ha cap element del tipus seleccionat al lloc triat
        if len(self.capa_tipus.nodes) < 1:
            iface.messageBar().pushMessage(
                u"No hi ha cap %s a %s" % (self.tipus, self.lloc),
                level=QgsMessageBar.CRITICAL,
                duration=10)
            self.dlg.tipus_usat.setText("Busca un tipus de recurs")
            return
        else:
            print(u"Capa de tipus de recurs a buscar (%s) creada amb %d "
                  "elements" % (self.tipus, len(self.capa_tipus.nodes)))


    def validar_distancia(self):
        u"""Valida que la distància sigui numèrica.

        Creo aquesta funció perquè ho demana l'anunciat, però no faria falta,
        ja que la "QsSpinBox" només deix introduir valors.
        """
        distancia = float(self.dlg.distancia.value())
        if type(distancia) is float:
            self.distancia = distancia
            print(u"Distància introduida: %d" % (self.distancia))
        else:
            iface.messageBar().pushMessage(
                u"Introdueix un valor enter",
                level=QgsMessageBar.CRITICAL,
                duration=10)


    def obte_llista_capa_objecte(self):
        """Retorna una llista de capes objecte."""
        self.dlg.capa_objecte_list.clear()
        self.capa_objecte = None
        self.entitat = None
        self.dlg.entitat_select.clear()
        self.dlg.entitat.clear()
        self.dlg.capa_objecte_usat.setText("Selecciona una capa de la llista")
        self.dlg.entitat_usat.setText(u"Selecciona una entitat de la llista")

        if not self.lloc:
            iface.messageBar().pushMessage(
                u"Primer has de seleccionar el lloc on fer la cerca",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )
            return

        capa_objecte = self.dlg.capa_objecte.text().encode('utf-8')

        llista_amenities = requests.get(AMENITIES)
        llista_amenities = llista_amenities.json()

        for element in llista_amenities['data']:
            if element['value']:
                if capa_objecte.lower() in (str(element['value'].
                                                encode('utf-8')).lower()):
                    self.dlg.capa_objecte_list.addItem(element['value'])

        print (u"Trobades %d capes" % (self.dlg.capa_objecte_list.count()))
        if self.dlg.capa_objecte_list.count() < 1:
            iface.messageBar().pushMessage(
                u"No hi ha cap capa amb %s. Torna-ho a provar"
                % (capa_objecte),
                level=QgsMessageBar.CRITICAL,
                duration=10
            )


    def obte_capa_objecte(self):
        """Retorna la capa objecte que s'ha de buscar."""
        self.nom_capa_objecte = self.dlg.capa_objecte_list.currentText()

        self.dlg.capa_objecte_usat.setText(self.nom_capa_objecte)

        self.capa_objecte = selecciona_capa(self.lloc, self.nom_capa_objecte)

        print(u"Comprovant si hi ha cap %s a %s" % (self.nom_capa_objecte,
                                                    self.lloc))

        if len(self.capa_objecte.nodes) < 1:
            iface.messageBar().pushMessage(
                u"No hi ha cap %s a %s" % (self.nom_capa_objecte, self.lloc),
                level=QgsMessageBar.CRITICAL,
                duration=10)
            self.dlg.capa_objecte_usat.setText("Busca la capa objecte")
            return
        else:
            print(u"Capa objecte (%s) creada amb %d elements" %
                  (self.nom_capa_objecte, len(self.capa_objecte.nodes)))

    def obte_llista_entitat(self):
        u"""Retorna una llista d'entitats de referència."""
        self.dlg.entitat_select.clear()
        # Comprovem que la variable self.capa_objecte té un valor
        if not self.capa_objecte:
            iface.messageBar().pushMessage(
                u"Primer has de seleccionar una capa objecte",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )
            return

        # Fem el mateix que hem fet per obtenir el valor de la variable
        # self.tipus i self.nom_capa_objecte
        entitat = self.dlg.entitat.text().encode('utf-8')

        for node in self.capa_objecte.nodes:
            if 'name' in node.tags.keys():
                if entitat.lower() in (str(node.tags['name'].encode('utf-8')).
                                       lower()):
                    self.dlg.entitat_select.addItem(node.tags['name'])

        print (u"Trobades %d entitats" % (self.dlg.entitat_select.count()))
        if self.dlg.entitat_select.count() < 1:
            iface.messageBar().pushMessage(
                u"No hi ha cap entiat amb %s. Torna-ho a provar" % (entitat),
                level=QgsMessageBar.CRITICAL,
                duration=10
            )


    def obte_entitat(self):
        u"""Selecciona l'entitat de referència."""
        nom_entitat = str(self.dlg.entitat_select.currentText().
                          encode('utf-8'))
        # Per trobar l'entitat entre la llista d'entitats que tenim a la
        # QComboBox, busquem l'entiat de la capa_objecte que coïncideix amb el
        # nom seleccionat a la QComboBox
        for node in self.capa_objecte.nodes:
            if 'name' in node.tags.keys():
                if nom_entitat == str(node.tags['name'].encode('utf-8')):
                    self.entitat = node
                    break

        self.dlg.entitat_usat.setText(self.entitat.tags['name'])

        print(u"Entitat %s creada" % (self.entitat.tags['name']))


    def busca_entitats(self):
        u"""Busca les entitats en funció del patrò de busca."""
        # Comprovem que totes les variables tenen valors
        if not self.lloc:
            iface.messageBar().pushMessage(
                u"Selecciona un lloc on fer la cerca!!!",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )
        elif not self.tipus:
            iface.messageBar().pushMessage(
                u"Selecciona el tipus de recurs a cercar!!!",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )

        elif self.distancia == 0:
            iface.messageBar().pushMessage(
                u"La distància ha de ser superior a 0",
                level=QgsMessageBar.CRITICAL,
                duration=10)

        elif not self.capa_objecte:
            iface.messageBar().pushMessage(
                u"Selecciona una capa de l'objecte a cercar!!!",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )

        elif not self.entitat:
            iface.messageBar().pushMessage(
                u"Selecciona l'entitat a cercar!!!",
                level=QgsMessageBar.CRITICAL,
                duration=10
                )

        # Si totes les variables tenen valors executa les funcions per crear la
        # capa
        else:
            buffer = self.genera_buffer()
            entitats = self.elements_dins_de(buffer)
            self.mostra_resultat(entitats)


    def genera_buffer(self):
        """Genera un buffer."""
        # Creem un objecte de tipus QgsGeometry per poder transformar la
        # geometria
        punt = QgsGeometry.fromPoint(
                    QgsPoint(float(self.entitat.lon), float(self.entitat.lat)))

        # Transformo la geometria de la entitat a un sistema mètric
        source = QgsCoordinateReferenceSystem(4326)
        target = QgsCoordinateReferenceSystem(25831)
        tr = QgsCoordinateTransform(source, target)
        punt.transform(tr)

        # Generem el buffer
        buffer = punt.buffer(self.distancia, 10)

        # Tornem al sistema de referència inicial
        inv_tr = QgsCoordinateTransform(target, source)
        punt.transform(inv_tr)
        buffer.transform(inv_tr)

        # Generem un missatge per saber si s'ha creat el buffer
        if buffer:
            print(u"Buffer generat")
            iface.messageBar().pushMessage(
                u"Buffer generat",
                level=QgsMessageBar.INFO,
                duration=10)
        else:
            iface.messageBar().pushMessage(
                u"No s'ha pogut generar el buffer",
                level=QgsMessageBar.CRITICAL,
                duration=10)

        return buffer


    def elements_dins_de(self, buffer):
        """Retorna els elements que estan dins del buffer."""
        # Creem un llista per emmagatzemar els elements que estan dins del
        # buffer
        llista_elements = []
        id = 0

        # Itinerem per tots els nodes
        for element in self.capa_tipus.nodes:
            # Convertim el node en un element QgsGeometry
            pt = QgsPoint(float(element.lon), float(element.lat))
            punt = QgsGeometry.fromPoint(pt)
            if punt.intersects(buffer):
                id += 1
                feature = QgsFeature()
                feature.setGeometry(punt)
                feature.setAttributes(list(element.tags))
                llista_elements.append(feature)

        print(u"Llista de elements creada amb %i" % len(llista_elements))

        return llista_elements


    def mostra_resultat(self, resultat):
        """Mostra el resultat com una capa de QGIS."""
        # Comprovem que hi ha com a mínim un recurs per generar la capa
        if len(resultat):
            # Definim la variable layer, com un objecte de la classe
            # QgsVectorLayer. Li diem el tipus d'entitat, el sistema de
            # referència, el nom del fitxer i per últim el "memory" que vol dir
            # que no guardi la capa en un fitxer, sinó a la memoria.
            layer = QgsVectorLayer("Point?crs=epsg:4326",
                                   "%s a %.f m de %s a %s" % (
                                       self.tipus, self.distancia,
                                       self.entitat.tags['name'], self.lloc
                                   ),
                                   "memory")
            # Definim la taula de dades. En aquest cas hi fiquem dos variables,
            # tot i que degut a que les dades de OSM no són homogènies (a
            # nivell de quantiat), no podem definir els mateixos atributs per a
            # tots els elements.
            pr = layer.dataProvider()
            pr.addAttributes([
                QgsField("id", QVariant.Int),
                QgsField("name", QVariant.String)
            ])
            pr.addFeatures(resultat)
            layer.commitChanges()

            # Afegim la capa al mapa
            QgsMapLayerRegistry.instance().addMapLayer(layer)

            # Li diem l'extenció que volem que ens mostri el mapa
            extent = layer.extent()
            iface.mapCanvas().setExtent(extent)

        # Si no hi ha cap recurs, enviem un missatge avisant que no podem crear
        # la capa
        else:
            iface.messageBar().pushMessage(
                u"No hi ha cap %s a %d metres de %s a %s" %
                (self.tipus, self.distancia, self.entitat.tags['name'],
                 self.lloc),
                level=QgsMessageBar.CRITICAL,
                duration=10)


    def neteja(self):
        """Neteja tots els camps dels atributs."""
        self.dlg.lloc.clear()
        self.dlg.lloc_usat.setText("Busca el lloc a on acotar la cerca")
        self.lloc = None
        self.dlg.tipus.clear()
        self.dlg.tipus_selec.clear()
        self.dlg.tipus_usat.setText("Selecciona un tipus de la llista")
        self.tipus = None
        self.dlg.distancia.setValue(0)
        self.distancia = 0
        self.dlg.capa_objecte.clear()
        self.dlg.capa_objecte_list.clear()
        self.dlg.capa_objecte_usat.setText("Selecciona una capa de la llista")
        self.capa_objecte = None
        self.dlg.entitat.clear()
        self.dlg.entitat_select.clear()
        self.dlg.entitat_usat.setText(u"Selecciona una entitat de la llista")
        self.entitat = None
