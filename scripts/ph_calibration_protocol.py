from pioreactor.calibrations import CalibrationProtocol
from pioreactor.structs import CalibrationBase, PolyFitCoefficients
from pioreactor.utils.timing import current_utc_datetime
from pioreactor.whoami import get_unit_name
from typing import ClassVar
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
    target_device: ClassVar[str] = "ph_probe"
    protocol_name: ClassVar[str] = "buffer_based"
    title: ClassVar[str] = "Buffer-based pH calibration"
    description: ClassVar[str] = "Calibrate the pH sensor using buffer solutions at pH 4, 7, and 10"

    def run(self, target_device: str) -> PHCalibration:
        return run_ph_calibration()


def calculate_poly_curve_of_best_fit(x: list[float], y: list[float], degree: int) -> list[float]:
    import numpy as np

    try:
        coefs = np.polyfit(x, y, deg=degree)
    except Exception as e:
        print(f"Unable to fit: {e}")
        coefs = np.zeros(degree + 1)

    return coefs.tolist()


def run_ph_calibration() -> PHCalibration:
    unit_name = get_unit_name()

    # Calibration data from buffer solutions
    # pH values: 4, 7, 10 (measured twice for validation)
    recorded_xs = [4, 7, 10, 4, 7, 10]

    # Corresponding voltage readings
    recorded_ys = [1.49, 1.12, 0.81, 1.48, 1.12, 0.81]

    # Fit a linear curve (degree 1 polynomial)
    curve_data = calculate_poly_curve_of_best_fit(recorded_xs, recorded_ys, 1)

    return PHCalibration(
        calibration_name=f"pH-{current_utc_datetime().strftime('%Y-%m-%d')}",
        created_at=current_utc_datetime(),
        curve_data_=PolyFitCoefficients(coefficients=curve_data),
        curve_type="poly",
        x="pH",
        y="Voltage",
        recorded_data={"x": recorded_xs, "y": recorded_ys},
        calibrated_on_pioreactor_unit=unit_name,
        electrode_type="Vernier-FPH"
    )
