from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import requests # <-- NUEVO

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    datos = request.json
    simbolo = datos.get('ticker', '').strip().upper()
    inversion_inicial = float(datos.get('inversionInicial', 0))
    aportacion_mensual = float(datos.get('aportacionMensual', 0))
    anios_proyeccion = int(datos.get('anios', 0))
    
    comision_anual = 0.0
    precio_actual = 0.0
    tasa_historica_anual = 0.0
    anios_reales_analizados = 0.0
    nombre_empresa = simbolo
    
    try:
        # <-- INICIO DE LA SOLUCIÓN: Disfrazamos la conexión -->
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Le pasamos la sesión "disfrazada" a yfinance
        ticker = yf.Ticker(simbolo, session=session)
        historial = ticker.history(period=f"{anios_proyeccion}y")
        
        # Validación: Si Yahoo nos bloquea y devuelve vacío, lanzamos un error
        if historial.empty or len(historial) < 2:
            return jsonify({'error': 'Yahoo Finance bloqueó la conexión o no hay datos para este Ticker.'}), 400
        # <-- FIN DE LA SOLUCIÓN -->

        precio_actual = historial['Close'].iloc[-1]
        precio_inicial = historial['Close'].iloc[0]
        
        dias_historia = (historial.index[-1] - historial.index[0]).days
        anios_reales_analizados = dias_historia / 365.25
        
        if anios_reales_analizados > 0:
            tasa_historica_anual = (precio_actual / precio_inicial) ** (1 / anios_reales_analizados) - 1
        
        info = ticker.info
        nombre_empresa = info.get('shortName') or info.get('longName') or simbolo
        tipo_activo = info.get('quoteType', 'Desconocido')
        
        if tipo_activo in ['ETF', 'MUTUALFUND']:
            comision_anual = info.get('annualReportExpenseRatio') or info.get('expenseRatio') or 0.0
                
    except Exception as e:
        return jsonify({'error': 'No se pudo obtener la información.'}), 400
        
    # Matemáticas
    tasa_neta_anual = tasa_historica_anual - comision_anual
    tasa_neta_mensual = tasa_neta_anual / 12
    meses_futuros = anios_proyeccion * 12
    
    monto_inicial_crecido = inversion_inicial * ((1 + tasa_neta_mensual)**meses_futuros)
    
    if tasa_neta_mensual > 0:
        monto_aportaciones = aportacion_mensual * (((1 + tasa_neta_mensual)**meses_futuros - 1) / tasa_neta_mensual)
    else:
        monto_aportaciones = aportacion_mensual * meses_futuros
        
    monto_final_bruto = monto_inicial_crecido + monto_aportaciones
    total_invertido = inversion_inicial + (aportacion_mensual * meses_futuros)
    
    ganancia_capital = monto_final_bruto - total_invertido
    impuesto_pagar = ganancia_capital * 0.10 if ganancia_capital > 0 else 0
    monto_total_ahorrado = monto_final_bruto - impuesto_pagar
    
    return jsonify({
        'nombre_empresa': nombre_empresa,
        'precio_actual': precio_actual,
        'comision_anual': comision_anual,
        'tasa_historica': tasa_historica_anual,
        'anios_historicos_usados': anios_reales_analizados,
        'total_invertido': total_invertido,
        'ganancia_capital': ganancia_capital,
        'impuesto_pagar': impuesto_pagar,
        'monto_total_ahorrado': monto_total_ahorrado
    })

if __name__ == '__main__':
    app.run(debug=True)
