from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import requests

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
    gasto_anual_actual = float(datos.get('gastoAnual', 0))  # Dato opcional
    
    comision_anual = 0.0
    precio_actual = 0.0
    tasa_historica_anual = 0.0
    anios_reales_analizados = 0.0
    nombre_empresa = simbolo
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        ticker = yf.Ticker(simbolo, session=session)
        historial = ticker.history(period=f"{anios_proyeccion}y")
        
        if historial.empty or len(historial) < 2:
            return jsonify({'error': 'No se encontraron datos históricos para este Ticker.'}), 400

        precio_actual = historial['Close'].iloc[-1]
        precio_inicial = historial['Close'].iloc[0]
        
        dias_historia = (historial.index[-1] - historial.index[0]).days
        anios_reales_analizados = dias_historia / 365.25
        
        if anios_reales_analizados > 0:
            tasa_historica_anual = (precio_actual / precio_inicial) ** (1 / anios_reales_analizados) - 1
        
        info = ticker.info
        nombre_empresa = info.get('shortName') or info.get('longName') or simbolo
        tipo_activo = info.get('quoteType', 'Desconocido')
        
        # SOLUCIÓN: Doble validación para extraer comisiones de ETFs
        comisiones_respaldo = {'VOO': 0.0003, 'IVV': 0.0003, 'SPY': 0.0009, 'VT': 0.0007, 'QQQ': 0.0020}
        
        if tipo_activo in ['ETF', 'MUTUALFUND'] or simbolo in comisiones_respaldo:
            comision_anual = info.get('expenseRatio') or info.get('annualReportExpenseRatio')
            if comision_anual is None:  # Si Yahoo falla, usamos el respaldo
                comision_anual = comisiones_respaldo.get(simbolo, 0.0)
                
    except Exception as e:
        return jsonify({'error': 'Error de conexión al obtener la información.'}), 400
        
    # Matemáticas e Interés Compuesto mediante iteración mensual
    tasa_neta_anual = tasa_historica_anual - comision_anual
    tasa_neta_mensual = tasa_neta_anual / 12
    meses_futuros = anios_proyeccion * 12
    
    saldo_inversion = inversion_inicial
    total_invertido = inversion_inicial
    comision_plataforma = 499.0  # Descuento anual por uso de plataforma (MXN)
    
    for mes in range(1, meses_futuros + 1):
        saldo_inversion = saldo_inversion * (1 + tasa_neta_mensual) + aportacion_mensual
        total_invertido += aportacion_mensual
        
        # Descontar comisión operativa de la plataforma al final de cada año
        if mes % 12 == 0:
            saldo_inversion -= comision_plataforma
            
    monto_final_bruto = max(0, saldo_inversion)
    
    # Impuestos por enajenación de acciones
    ganancia_capital = monto_final_bruto - total_invertido
    impuesto_pagar = ganancia_capital * 0.10 if ganancia_capital > 0 else 0
    monto_total_ahorrado = monto_final_bruto - impuesto_pagar
    
    # Cálculo de longevidad del dinero considerando inflación (Promedio MX 4.5%)
    gasto_futuro_proyectado = 0
    anios_supervivencia = 0
    tasa_inflacion = 0.045 
    
    if gasto_anual_actual > 0:
        # Se infla el gasto anual actual hacia el futuro
        gasto_futuro_proyectado = gasto_anual_actual * ((1 + tasa_inflacion) ** anios_proyeccion)
        if gasto_futuro_proyectado > 0:
            anios_supervivencia = monto_total_ahorrado / gasto_futuro_proyectado
    
    return jsonify({
        'nombre_empresa': nombre_empresa,
        'precio_actual': precio_actual,
        'comision_anual': comision_anual,
        'tasa_historica': tasa_historica_anual,
        'anios_historicos_usados': anios_reales_analizados,
        'total_invertido': total_invertido,
        'ganancia_capital': ganancia_capital,
        'impuesto_pagar': impuesto_pagar,
        'monto_total_ahorrado': monto_total_ahorrado,
        'gasto_futuro': gasto_futuro_proyectado,
        'anios_supervivencia': anios_supervivencia
    })

if __name__ == '__main__':
    app.run(debug=True)
