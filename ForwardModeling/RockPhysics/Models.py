import numpy as np
import multiprocessing as mp
from scipy import interpolate

from ForwardModeling.RockPhysics.Mediums.VoigtReussHill import voigt
from ForwardModeling.RockPhysics.Mediums.DEMSlb import DEM
from ForwardModeling.RockPhysics.Mediums import Gassmann
from ForwardModeling.RockPhysics import Tools


def simple_model_1(Km, Gm, Ks, Gs, Kf, phi, phi_s, rho_s, rho_f, rho_m, Vm=None, alpha=0.1):
    '''
    Самый простой вариант модели (для одного слоя!)
    :param Km: Массив модулей сжатия минералов скелета
    :param Gm: Массив модулей сдвига минералов скелета
    :param Ks: Модуль сжатия глин
    :param Gs: Модуль сдвига глин
    :param Kf: Модуль сжатия флюида
    :param phi: Пористость
    :param phi_s: Коэффициент глинистости
    :param rho_s: Плотность глин
    :param rho_f: Плотность флюида
    :param rho_m: Плотность скелета
    :param Vm: Компоненты минералов (их сумма должна быть равна 1)
    :param alpha: Аспектное соотношение?..
    :return: Vp, Vs, Rho
    '''

    if Vm is None:
        Vm = [1]

    # Осреднение упругих модулей скелета
    if type(Km) == np.ndarray:
        Km_ = voigt(Km, Vm)

    else:
        Km_ = Km

    if type(Gm) == np.ndarray:
        Gm_ = voigt(Gm, Vm)

    else:
        Gm_ = Gm

    # Кол-во твердого матрикса
    phi_m = 1 - phi

    # Упругие модули твердого матрикса
    Km_ = voigt(np.array([Km_, Ks]), np.array([(phi_m - phi_s) / phi_m, phi_s / phi_m]))
    Gm_ = voigt(np.array([Gm_, Gs]), np.array([(phi_m - phi_s) / phi_m, phi_s / phi_m]))

    if phi > 0:
        # Создание дыр в "сухой" породе
        K_dry, G_dry = DEM(Km_, Gm_, 0, 0, phi, alpha)

        if Kf > 0:
            # Заливаем флюид по Гассману
            K_res = Gassmann.Ks(K_dry, Km_, Kf, phi)

        else:
            K_res = K_dry

        G_res = G_dry

    else:
        K_res = Km_
        G_res = Gm_




    # Осредняем плотность скелета
    Rho_m = voigt(rho_m, Vm)

    # Осредняем все плотности до результирующей
    rho_res = rho_s*phi_s + rho_f*phi + (1 - (phi + phi_s))*Rho_m

    return [Tools.vp_from_KGRho(K_res, G_res, rho_res), Tools.vs_from_GRho(G_res, rho_res), rho_res]


def model_calculation_mp_helper(args):
    return simple_model_1(*args)


def model_calculation(nlayers, Km, Gm, Ks, Gs, Kf, phi, phi_s, rho_s, rho_f, rho_m, Vm=None, alpha=None, mp_cond=False):

    result_models = []

    if Vm is None:
        Vm = [1]*nlayers

    if alpha is None:
        alpha = [0.1]*nlayers

    if mp_cond:
        ncpu = mp.cpu_count()
        nproc = 1 * ncpu

        input_args = np.column_stack((Km, Gm, Ks, Gs, Kf, phi, phi_s, rho_s, rho_f, rho_m, Vm, alpha))

        with mp.Pool(processes=nproc) as pool:
            result_models = pool.map(model_calculation_mp_helper, input_args)

    else:
        for i in range(nlayers):
            res_model = simple_model_1(Km[i], Gm[i], Ks[i], Gs[i], Kf[i], phi[i], phi_s[i], rho_s[i], rho_f[i], rho_m[i],
                                            Vm[i], alpha[i])

            result_models.append(res_model)

    result_models = np.array(result_models)

    vp = result_models[:, 0]*1000
    vs = result_models[:, 1]*1000
    rho = result_models[:, 2]*1000

    return vp, vs, rho



