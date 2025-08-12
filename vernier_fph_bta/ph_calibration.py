from pioreactor.calibrations import CalibrationProtocol
from pioreactor.structs import CalibrationBase
from pioreactor.utils.timing import current_utc_datetime
from pioreactor.whoami import get_unit_name
import typing as t

class PHCalibration(CalibrationBase, kw_only=True, tag="ph"):

    electrode_type: str
    x: str = "pH"
    y: str = "Voltage"

    def voltage_to_ph(self, voltage: float) -> float:
        return self.y_to_x(voltage)
    def ph_to_voltage(self, ph: float) -> float:
        return self.x_to_y(ph)

class BufferBasedPHProtocol(CalibrationProtocol):
    target_device = "ph_probe"
    protocol_name = "buffer_based"
    description = "Calibrate the pH sensor using buffer solutions"

    def run(self, target_device: str) -> PHCalibration:
        return run_ph_calibration()

def calculate_poly_curve_of_best_fit(x: list[float], y: list[float], degree: int) -> list[float]:
    import numpy as np

    try:
        coefs = np.polyfit(x, y, deg=degree)
    except Exception:
        print("Unable to fit.")
        coefs = np.zeros(degree)

    return coefs.tolist()

def run_ph_calibration() -> PHCalibration:


    unit_name = get_unit_name()

    # run the calibration

    recorded_xs = [4,7,10,4,7,10] 
    recorded_ys = [1.50, 1.14, 0.78, 1.51, 1.14, 0.78] 

    curve_data = calculate_poly_curve_of_best_fit(recorded_xs, recorded_ys,  1)

    return PHCalibration(
        calibration_name=f"pH-{current_utc_datetime().strftime('%Y-%m-%d')}",
        created_at=current_utc_datetime(),
        curve_data_ = curve_data, # ax1, intercept
        curve_type="poly",
        x="pH",
        y="Voltage",
        recorded_data={"x":recorded_xs, "y": recorded_ys},
        calibrated_on_pioreactor_unit = unit_name,
        electrode_type="Vernier-FPH"
    )


