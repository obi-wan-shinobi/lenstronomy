import numpy as np
import lenstronomy.Util.constants as const
from lenstronomy.GalKin.light_profile import LightProfile
from lenstronomy.GalKin.mass_profile import MassProfile
from lenstronomy.GalKin.anisotropy import Anisotropy
from lenstronomy.GalKin.cosmo import Cosmo


class NumericKinematics(Anisotropy):

    def __init__(self, mass_profile_list, light_profile_list, anisotropy_model='isotropic',
                 kwargs_cosmo={'D_d': 1000, 'D_s': 2000, 'D_ds': 500}, interpol_grid_num=500, log_integration=False,
                 max_integrate=10, min_integrate=0.001):
        """

        :param interpol_grid_num:
        :param log_integration:
        :param max_integrate:
        :param min_integrate:
        """
        self._interp_grid_num = interpol_grid_num
        self._log_int = log_integration
        self._max_integrate = max_integrate  # maximal integration (and interpolation) in units of arcsecs
        self._min_integrate = min_integrate  # min integration (and interpolation) in units of arcsecs
        self.massProfile = MassProfile(mass_profile_list, kwargs_cosmo, interpol_grid_num=interpol_grid_num,
                                         max_interpolate=max_integrate, min_interpolate=min_integrate)
        self.lightProfile = LightProfile(light_profile_list, interpol_grid_num=interpol_grid_num,
                                         max_interpolate=max_integrate, min_interpolate=min_integrate)
        Anisotropy.__init__(self, anisotropy_type=anisotropy_model)
        self.cosmo = Cosmo(**kwargs_cosmo)

    def _sigma2_R(self, R, kwargs_mass, kwargs_light, kwargs_anisotropy):
        """
        returns unweighted los velocity dispersion for a specified projected radius

        :param R: 2d projected radius (in angular units of arcsec)
        :param kwargs_mass: mass model parameters (following lenstronomy lens model conventions)
        :param kwargs_light: deflector light parameters (following lenstronomy light model conventions)
        :param kwargs_anisotropy: anisotropy parameters, may vary according to anisotropy type chosen.
            We refer to the Anisotropy() class for details on the parameters.
        :return:
        """
        I_R_sigma2 = self._I_R_simga2(R, kwargs_mass, kwargs_light, kwargs_anisotropy)
        I_R = self.lightProfile.light_2d(R, kwargs_light)
        return I_R_sigma2 / I_R

    def _I_R_simga2(self, R, kwargs_mass, kwargs_light, kwargs_anisotropy):
        """
        equation A15 in Mamon&Lokas 2005 as a logarithmic numerical integral (if option is chosen)
        modulo pre-factor 2*G

        :param R: 2d projected radius (in angular units)
        :param kwargs_mass: mass model parameters (following lenstronomy lens model conventions)
        :param kwargs_light: deflector light parameters (following lenstronomy light model conventions)
        :param kwargs_anisotropy: anisotropy parameters, may vary according to anisotropy type chosen.
            We refer to the Anisotropy() class for details on the parameters.
        :return: integral of A15 in Mamon&Lokas 2005
        """
        R = max(R, self._min_integrate)
        if self._log_int is True:
            min_log = np.log10(R+0.001)
            max_log = np.log10(self._max_integrate)
            r_array = np.logspace(min_log, max_log, self._interp_grid_num)
            dlog_r = (np.log10(r_array[2]) - np.log10(r_array[1])) * np.log(10)
            IR_sigma2_dr = self._integrand_A15(r_array, R, kwargs_mass, kwargs_light, kwargs_anisotropy) * dlog_r * r_array
        else:
            r_array = np.linspace(R+0.001, self._max_integrate, self._interp_grid_num)
            dr = r_array[2] - r_array[1]
            IR_sigma2_dr = self._integrand_A15(r_array, R, kwargs_mass, kwargs_light, kwargs_anisotropy) * dr
        IR_sigma2 = np.sum(IR_sigma2_dr) * const.arcsec * self.cosmo.dd  # integral from angle to physical scales
        return IR_sigma2

    def _integrand_A15(self, r, R, kwargs_mass, kwargs_light, kwargs_anisotropy):
        """
        integrand of A15 (in log space) in Mamon&Lokas 2005

        :param r: 3d radius in arc seconds
        :param R: 2d projected radius
        :param kwargs_mass: mass model parameters (following lenstronomy lens model conventions)
        :param kwargs_light: deflector light parameters (following lenstronomy light model conventions)
        :param kwargs_anisotropy: anisotropy parameters, may vary according to anisotropy type chosen.
            We refer to the Anisotropy() class for details on the parameters.
        :return:
        """
        k_r = self.K(r, R, **kwargs_anisotropy)
        l_r = self.lightProfile.light_3d_interp(r, kwargs_light)
        m_r = self.massProfile.mass_3d_interp(r, kwargs_mass)
        out = k_r * l_r * m_r / r
        return out
