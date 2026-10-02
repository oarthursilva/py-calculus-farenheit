from flask import Blueprint, request, jsonify

from services import toFahrenheit

fahrenheit = Blueprint('fahrenheit', __name__)


@fahrenheit.route('/fahrenheit', methods=['GET'])
def fahrenheitController():
    """Convert to fahrenheit"""
    temp_f_its90 = request.args.get('temp_f_its90', type=float)
    api60 = request.args.get('api60', type=float)
    pressure_psig = request.args.get('pressure_psig', type=float)

    if temp_f_its90 is None:
        return jsonify({'error': 'missing value: "temp_f_its90"}'}), 400

    if api60 is None:
        return jsonify({'error': 'missing value: "api60"}'}), 400

    if pressure_psig is None:
        return jsonify({'error': 'missing value: "pressure_psig"}'}), 400

    return toFahrenheit(temp_f_its90, api60, pressure_psig), 200, {}