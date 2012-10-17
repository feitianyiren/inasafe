# -*- coding: utf-8 -*-
"""**Postprocessors package.**

"""

__author__ = 'Marco Bernasocchi <marco@opengis.ch>'
__revision__ = '$Format:%H$'
__date__ = '10/10/2012'
__license__ = "GPL"
__copyright__ = 'Copyright 2012, Australia Indonesia Facility for '
__copyright__ += 'Disaster Reduction'

from safe.postprocessors.abstract_postprocessor import (
                                                    AbstractPostprocessor)

from safe.common.utilities import ugettext as tr

class GenderPostprocessor(AbstractPostprocessor):
    def __init__(self):
        AbstractPostprocessor.__init__(self)
        self.population_total = None
        self.female_ratio = None

    def setup(self, params):
        """concrete implementation it takes care of the needed parameters being
         initialized

        Args:
            params: Dict of parameters to pass to the post processor
        Returns:
            None
        Raises:
            None
        """
        AbstractPostprocessor.setup(self, None)
        if self.population_total is not None or self.female_ratio is not None:
            self._raise_error('clear needs to be called before setup')
        self.population_total = params['population_total']
        self.female_ratio = params['female_ratio']

    def process(self):
        """concrete implementation it takes care of the needed parameters being
         available and performs all the indicators calculations

        Args:
            None
        Returns:
            None
        Raises:
            None
        """
        AbstractPostprocessor.process(self)
        if self.population_total is None or self.female_ratio is None:
            self._raise_error('setup needs to be called before process')
        self._calculate_total()
        self._calculate_females()
        self._calculate_weekly_hygene_packs()
        self._calculate_weekly_increased_calories()

    def clear(self):
        """concrete implementation it takes care of the needed parameters being
         properly cleared

        Args:
            None
        Returns:
            None
        Raises:
            None
        """
        AbstractPostprocessor.clear(self)
        self.population_total = None
        self.female_ratio = None

    def _calculate_total(self):
        myName = tr('Total')
        myResult = self.population_total
        myResult = int(round(myResult))
        self._append_result(myName, myResult)

    def _calculate_females(self):
        myName = tr('Female population')
        myResult = self.population_total * self.female_ratio
        myResult = int(round(myResult))
        self._append_result(myName, myResult)

    def _calculate_weekly_hygene_packs(self):
        myName = tr('Weekly hygiene packs')
        myMeta = {'description': 'Females hygiene packs for weekly use'}
        #weekly hygene packs =
        # affected pop * fem_ratio * 0.7937 * week / intended day-of-use
        myResult = self.population_total * self.female_ratio * 0.7937 * (7 / 7)
        myResult = int(round(myResult))
        self._append_result(myName, myResult, myMeta)

    def _calculate_weekly_increased_calories(self):
        myName = tr('Additional weekly rice kg for pregnant and lactating'
                         ' women')
        myMeta = {'description': 'Additional rice kg per week for pregnant and'
                                 ' lactating women'}
        #weekly Kg rice =
        # affected pop * fem_ratio * 0.7937 * week / intended day-of-use
        myLactKg = self.population_total * self.female_ratio * 2 * 0.033782
        myPregKg = self.population_total * self.female_ratio * 2 * 0.01281
        myResult = myLactKg + myPregKg
        myResult = int(round(myResult))
        self._append_result(myName, myResult, myMeta)
