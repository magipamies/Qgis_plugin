# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BuscaRecursos
                                 A QGIS plugin
 Buscador de recursos
                             -------------------
        begin                : 2019-04-11
        copyright            : (C) 2019 by Magí Pàmies Sans
        email                : magipamies@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load BuscaRecursos class from file BuscaRecursos.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .busca_recursos import BuscaRecursos
    return BuscaRecursos(iface)
