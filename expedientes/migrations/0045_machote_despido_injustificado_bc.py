"""
Machote: Demanda laboral por despido injustificado — Tribunal Laboral de B.C.

Basado en demandas/DEMANDA LABORAL POR DESPIDO INJUSTIFICADO.pdf, con los
datos del caso original reemplazados por marcadores {{ ... }} (se llenan con
el expediente) y [CORCHETES] para hechos que el asesor debe redactar.
"""

from django.db import migrations

ARCHIVO_ORIGEN = 'DEMANDA LABORAL POR DESPIDO INJUSTIFICADO.pdf'

CONTENIDO_HTML = """<h2 style="text-align:center;">DEMANDA LABORAL POR DESPIDO INJUSTIFICADO</h2>

<p><strong>C. JUEZ DEL TRIBUNAL LABORAL DEL PODER JUDICIAL DEL ESTADO DE BAJA CALIFORNIA, EN TURNO.<br>P R E S E N T E.</strong></p>

<p><strong>{{ nombre_cliente }}</strong>, por mi propio derecho, señalando como domicilio para oír y recibir notificaciones el ubicado en [DOMICILIO PARA NOTIFICACIONES], de esta ciudad de Tijuana, Baja California, y designando como mis apoderados legales a los licenciados HANS LUNA HERNÁNDEZ, RICARDO PEÑALOZA CRUZ y CHRISTIAN JESÚS GARCÍA SANTOYO, en términos de la carta poder y documentos de representación que se acompañen, respetuosamente comparezco para exponer:</p>

<p>Que por medio del presente escrito, en ejercicio de mis derechos laborales y con fundamento en el artículo 123, apartado A, de la Constitución Política de los Estados Unidos Mexicanos, así como en las disposiciones aplicables de la Ley Federal del Trabajo, vengo a demandar en la vía ordinaria laboral a:</p>

<p><strong>1. {{ nombre_empresa }}</strong>, y/o QUIEN RESULTE SER EL PROPIETARIO, PATRÓN, REPRESENTANTE LEGAL O RESPONSABLE DE LA FUENTE DE TRABAJO.</p>

<p>Con domicilio para su emplazamiento en:<br>{{ direccion_empresa }}, Tijuana, Baja California.</p>

<p>Lo anterior, sin perjuicio de que durante el procedimiento se determine la identidad y razón social de la persona física o moral que efectivamente fungió como patrón y recibió los servicios personales subordinados del suscrito.</p>

<p>La presente demanda se promueve con motivo del despido injustificado del que fui objeto el día {{ fecha_despido }}, reclamando el pago de las siguientes:</p>

<h3 style="text-align:center;">I. PRESTACIONES RECLAMADAS</h3>

<p><strong>A) INDEMNIZACIÓN CONSTITUCIONAL.</strong><br>El pago de tres meses de salario integrado, equivalente a la indemnización constitucional que corresponde por el despido injustificado del que fui objeto, conforme al artículo 48 de la Ley Federal del Trabajo.</p>

<p><strong>B) SALARIOS VENCIDOS.</strong><br>El pago de los salarios vencidos que se generen desde la fecha del despido injustificado y hasta por el periodo máximo establecido en el artículo 48 de la Ley Federal del Trabajo, así como los intereses legales que procedan en caso de prolongarse el procedimiento en los términos previstos por dicho precepto.</p>

<p><strong>C) AGUINALDO PROPORCIONAL.</strong><br>El pago de la parte proporcional de aguinaldo correspondiente al tiempo efectivamente laborado durante el año {{ anio_actual }}, conforme al artículo 87 de la Ley Federal del Trabajo.</p>

<p><strong>D) VACACIONES PROPORCIONALES.</strong><br>El pago de las vacaciones proporcionales generadas durante el tiempo de prestación de servicios, de conformidad con los artículos 76 y 79 de la Ley Federal del Trabajo.</p>

<p><strong>E) PRIMA VACACIONAL.</strong><br>El pago de la prima vacacional correspondiente, equivalente al porcentaje mínimo legal del 25% sobre las vacaciones que resulten procedentes, conforme al artículo 80 de la Ley Federal del Trabajo.</p>

<p><strong>F) PRIMA DE ANTIGÜEDAD.</strong><br>El pago de la prima de antigüedad que legalmente corresponda, calculada en términos del artículo 162 de la Ley Federal del Trabajo y considerando el tiempo efectivamente laborado.</p>

<p><strong>G) SALARIOS DEVENGADOS Y NO PAGADOS.</strong><br>El pago de cualquier salario que se encuentre pendiente de cubrir por los días efectivamente trabajados hasta la fecha de separación, en caso de acreditarse que existió alguna cantidad insoluta.</p>

<p><strong>H) RECONOCIMIENTO DE LA RELACIÓN LABORAL.</strong><br>El reconocimiento judicial de la existencia de una relación laboral por tiempo indeterminado entre el suscrito y la parte demandada, durante el periodo comprendido del {{ fecha_ingreso }} al {{ fecha_despido }}, en términos de los artículos 20 y 21 de la Ley Federal del Trabajo, salvo que la demandada acredite legalmente una modalidad distinta.</p>

<p><strong>I) SEGURIDAD SOCIAL.</strong><br>Se declare el incumplimiento patronal consistente en no haber inscrito al suscrito ante el Instituto Mexicano del Seguro Social durante la relación laboral y se dé vista a las autoridades competentes para los efectos legales correspondientes, sin perjuicio de las obligaciones patronales de seguridad social que resulten acreditadas.</p>

<p><strong>J) DEMÁS PRESTACIONES.</strong><br>El pago de cualquier otra prestación laboral que resulte procedente conforme a los hechos acreditados y a la Ley Federal del Trabajo.</p>

<h3 style="text-align:center;">II. HECHOS</h3>

<p><strong>PRIMERO. INGRESO Y CONTRATACIÓN.</strong><br>El día {{ fecha_ingreso }} ingresé a prestar mis servicios personales subordinados para la fuente de trabajo que se identifica comercialmente como {{ nombre_empresa }}, en la ciudad de Tijuana, Baja California.</p>
<p>Al momento de mi contratación se me asignó el puesto de {{ puesto_trabajador }}, realizando actividades relacionadas con [DESCRIPCIÓN DE LAS ACTIVIDADES].</p>
<p>La contratación se realizó directamente con la fuente de trabajo, bajo las instrucciones y supervisión de sus representantes.</p>

<p><strong>SEGUNDO. CONDICIONES DE TRABAJO.</strong><br>Durante el tiempo que presté mis servicios, desempeñé una jornada de [DÍAS DE LA JORNADA], en un horario comprendido de las [HORA DE ENTRADA] a las [HORA DE SALIDA] horas.</p>
<p>Mi descanso semanal correspondía a los días [DÍAS DE DESCANSO].</p>
<p>Durante la jornada contaba con [PERIODOS DE DESCANSO DENTRO DE LA JORNADA].</p>
<p>El salario que se me indicó y pagaba la empresa era de {{ salario }} {{ periodo_pago }}, con pago los días [DÍA DE PAGO] y mediante [FORMA DE PAGO].</p>

<p><strong>TERCERO. SUBORDINACIÓN LABORAL.</strong><br>Durante la prestación de mis servicios me encontraba sujeto a las instrucciones, supervisión, organización y control de la parte patronal.</p>
<p>La empresa establecía mis actividades, horarios, funciones y mecanismos de control de asistencia.</p>
<p>Asimismo, contaba con [MECANISMO DE REGISTRO DE ENTRADAS Y SALIDAS] para registrar las entradas y salidas del personal.</p>
<p>Por lo anterior, mi prestación de servicios reunía las características de trabajo personal subordinado previstas en los artículos 20 y 21 de la Ley Federal del Trabajo.</p>

<p><strong>CUARTO. FALTA DE INSCRIPCIÓN ANTE EL IMSS.</strong><br>Durante el tiempo que presté mis servicios, la parte patronal no me dio de alta ante el Instituto Mexicano del Seguro Social, a pesar de existir una relación de trabajo subordinada.</p>
<p>En consecuencia, solicito que se investigue y determine el incumplimiento de las obligaciones patronales en materia de seguridad social, dando intervención a las autoridades competentes.</p>

<p><strong>QUINTO. DESPIDO INJUSTIFICADO.</strong><br>El día {{ fecha_despido }}, aproximadamente a las [HORA DEL DESPIDO] horas, me encontraba realizando mis actividades laborales habituales dentro de las instalaciones de la fuente de trabajo.</p>
<p>En ese momento, [NOMBRE Y CARGO DE QUIEN INTERVINO], cuyas características físicas corresponden a una persona de [MEDIA FILIACIÓN: ESTATURA, COMPLEXIÓN, TEZ, EDAD APROXIMADA], me indicó que [LO QUE SE LE INDICÓ].</p>
<p>[NARRACIÓN DE CÓMO, DÓNDE Y QUIÉN COMUNICÓ EL DESPIDO, CON MEDIA FILIACIÓN DE LA PERSONA].</p>
<p>Dicha persona me manifestó que me encontraba despedido y que debía retirarme de las instalaciones.</p>
<p>En ningún momento se me entregó aviso escrito de rescisión de la relación laboral, ni se me informó de alguna causa legal que justificara la terminación de mis servicios.</p>
<p>Por lo anterior, considero que fui objeto de un despido injustificado, sin que existiera causa legal que justificara la terminación de la relación laboral.</p>

<p><strong>SEXTO. AUSENCIA DE RENUNCIA.</strong><br>Manifiesto bajo protesta de decir verdad que no presenté renuncia voluntaria, no firmé documento de terminación de la relación laboral, no suscribí hojas en blanco ni recibí aviso de rescisión.</p>
<p>Tampoco manifesté mi voluntad de dar por terminada la relación de trabajo.</p>

<p><strong>SÉPTIMO. INTENTO DE CONCILIACIÓN PREJUDICIAL.</strong><br>Con fecha {{ fecha_tramite }} presenté solicitud de conciliación ante el Centro de Conciliación Laboral del Estado de Baja California, con sede en Tijuana, bajo el número de identificación único:</p>
<p style="text-align:center;"><strong>{{ folio_conciliacion }}</strong></p>
<p>Se señaló audiencia para el día {{ fecha_audiencia }} a las [HORA DE LA AUDIENCIA] horas, en la [SALA DE CONCILIACIÓN].</p>
<p>La parte citada, identificada como {{ nombre_empresa }}, fue debidamente notificada; sin embargo, no compareció a la audiencia.</p>
<p>Por tal motivo, el Centro de Conciliación Laboral expidió la correspondiente CONSTANCIA DE NO CONCILIACIÓN, de fecha {{ fecha_audiencia }}.</p>
<p>En consecuencia, se encuentra agotada la etapa de conciliación prejudicial obligatoria y expedita la vía jurisdiccional para reclamar mis derechos laborales.</p>

<h3 style="text-align:center;">III. DERECHO</h3>

<p>Son aplicables al presente asunto los siguientes ordenamientos:</p>
<p><strong>A) CONSTITUCIÓN POLÍTICA DE LOS ESTADOS UNIDOS MEXICANOS.</strong><br>Artículo 123, apartado A, en cuanto establece los derechos fundamentales de las personas trabajadoras y las obligaciones patronales derivadas de las relaciones laborales.</p>
<p><strong>B) LEY FEDERAL DEL TRABAJO.</strong></p>
<p>Artículos 2 y 3, relativos a los principios de trabajo digno y protección de los derechos laborales.</p>
<p>Artículos 8, 10, 20 y 21, relativos a la calidad de trabajador, patrón y existencia de la relación laboral.</p>
<p>Artículos 24, 25 y 26, relativos a las condiciones de trabajo y sus formalidades.</p>
<p>Artículos 35 y demás aplicables, relativos a la duración de las relaciones de trabajo.</p>
<p>Artículos 47 y 48, relativos a la rescisión de las relaciones laborales y las consecuencias del despido injustificado.</p>
<p>Artículos 76, 79 y 80, relativos a vacaciones y prima vacacional.</p>
<p>Artículo 87, relativo al aguinaldo.</p>
<p>Artículos 82, 84 y 89, relativos al salario y su integración para efectos indemnizatorios.</p>
<p>Artículos 132 y 804, relativos a las obligaciones patronales y conservación de documentos.</p>
<p>Artículos 784 y demás aplicables, relativos a las cargas probatorias.</p>
<p>Artículos 870, 871, 872 y demás relativos al procedimiento ordinario laboral.</p>
<p>Artículos 684-A, 684-B y demás relativos a la conciliación prejudicial.</p>

<h3 style="text-align:center;">IV. PRUEBAS</h3>

<p>Desde este momento ofrezco las siguientes pruebas, relacionadas con los hechos de la demanda:</p>

<p><strong>1. DOCUMENTAL PÚBLICA.</strong><br>Consistente en la CONSTANCIA DE NO CONCILIACIÓN expedida por el Centro de Conciliación Laboral del Estado de Baja California, de fecha {{ fecha_audiencia }}, correspondiente al expediente {{ folio_conciliacion }}.</p>
<p>Esta prueba se ofrece para acreditar que se agotó la etapa prejudicial obligatoria y que la parte demandada fue citada y no compareció.</p>

<p><strong>2. DOCUMENTAL PRIVADA.</strong><br>Consistente en cualquier contrato individual de trabajo, documento de contratación, identificación, gafete, comunicación o documentación relacionada con la prestación de servicios del suscrito, que obre en mi poder o que sea exhibida por la parte demandada.</p>
<p>Se relaciona con los hechos primero, segundo y tercero.</p>

<p><strong>3. INSPECCIÓN.</strong><br>Consistente en la inspección que deberá practicarse sobre los documentos, controles y registros que se encuentren bajo resguardo de la parte demandada, correspondientes al periodo comprendido del {{ fecha_ingreso }} al {{ fecha_despido }}, particularmente:</p>
<p>a) Contrato individual de trabajo del suscrito.<br>
b) Recibos de pago de salarios y nóminas.<br>
c) Controles de asistencia y registros de entrada y salida.<br>
d) Registros electrónicos del sistema de control de personal.<br>
e) Listas de raya y comprobantes de pago.<br>
f) Registros de alta y movimientos afiliatorios ante el Instituto Mexicano del Seguro Social.<br>
g) Documentos relativos a la terminación de la relación laboral.<br>
h) Aviso de rescisión, en caso de que la parte demandada sostenga que existió una causa justificada de terminación.</p>
<p>Lo anterior, para acreditar las condiciones de trabajo, salario, jornada, antigüedad, subordinación y circunstancias de la separación.</p>

<p><strong>4. CONFESIONAL.</strong><br>A cargo de la persona física o moral que resulte ser el patrón, por conducto de su representante legal o de la persona que conforme a la Ley deba absolver posiciones, para que responda sobre los hechos propios de la relación laboral y las circunstancias del despido.</p>

<p><strong>5. TESTIMONIAL.</strong><br>A cargo de las personas que tengan conocimiento directo de la relación laboral y de los hechos del despido, particularmente quienes se encontraban presentes o tuvieron conocimiento de la intervención de [PERSONAS QUE INTERVINIERON EN EL DESPIDO].</p>
<p>Los nombres y domicilios de los testigos se proporcionarán conforme a su identificación y disponibilidad.</p>

<p><strong>6. INSTRUMENTAL DE ACTUACIONES.</strong><br>Consistente en todas las actuaciones que se generen dentro del presente procedimiento y que favorezcan a los intereses del suscrito.</p>

<p><strong>7. PRESUNCIONAL LEGAL Y HUMANA.</strong><br>En todo aquello que favorezca a mis intereses, derivado de los hechos acreditados, las omisiones patronales y las presunciones establecidas por la legislación laboral.</p>

<h3 style="text-align:center;">V. PUNTOS PETITORIOS</h3>

<p>Por lo anteriormente expuesto y fundado, a este H. Tribunal atentamente solicito:</p>
<p><strong>PRIMERO.</strong> Tenerme por presentado con este escrito, promoviendo formal demanda laboral en contra de {{ nombre_empresa }} y/o quien resulte responsable de la fuente de trabajo.</p>
<p><strong>SEGUNDO.</strong> Admitir la demanda en la vía ordinaria laboral y reconocer la personalidad de mis apoderados legales, en caso de acreditarse debidamente su representación.</p>
<p><strong>TERCERO.</strong> Tener por exhibida la constancia de no conciliación expedida por el Centro de Conciliación Laboral del Estado de Baja California.</p>
<p><strong>CUARTO.</strong> Ordenar el emplazamiento de la parte demandada en el domicilio señalado, para que comparezca a juicio y dé contestación a la demanda.</p>
<p><strong>QUINTO.</strong> Requerir a la parte demandada para que exhiba los documentos laborales y registros que se encuentran bajo su resguardo y que resultan necesarios para esclarecer las condiciones de trabajo y la terminación de la relación laboral.</p>
<p><strong>SEXTO.</strong> Tener por ofrecidas las pruebas señaladas en el presente escrito y admitirlas conforme a derecho.</p>
<p><strong>SÉPTIMO.</strong> En su oportunidad, dictar sentencia definitiva en la que se declare que existió un despido injustificado y se condene a la parte demandada al pago de las prestaciones laborales reclamadas que resulten procedentes.</p>
<p><strong>OCTAVO.</strong> Dar vista a las autoridades competentes en materia de seguridad social, para los efectos legales que correspondan por la omisión de inscripción del trabajador ante el Instituto Mexicano del Seguro Social.</p>

<p style="text-align:center;"><strong>PROTESTO LO NECESARIO.</strong></p>
<p style="text-align:center;">Tijuana, Baja California, a {{ hoy }}.</p>
<br><br>
<p style="text-align:center;">________________________________________</p>
<p style="text-align:center;"><strong>{{ nombre_cliente }}</strong><br>ACTOR</p>
"""


def crear_machote(apps, schema_editor):
    Machote = apps.get_model('expedientes', 'Machote')
    Machote.objects.update_or_create(
        archivo_origen=ARCHIVO_ORIGEN,
        defaults={
            'nombre': 'Despido Injustificado - Tribunal Laboral B.C.',
            'descripcion': (
                'Demanda por despido injustificado ante el Tribunal Laboral del '
                'Poder Judicial de B.C. (Tijuana). Incluye reclamo por falta de '
                'alta en el IMSS; completar los datos entre [CORCHETES].'
            ),
            'categoria': 'demanda',
            'tipo_despido': 'injustificado',
            'jurisdiccion': 'estatal',
            'contenido_html': CONTENIDO_HTML,
            'icono': '⚖️',
            'activo': True,
            'orden': 1,
        },
    )


def eliminar_machote(apps, schema_editor):
    Machote = apps.get_model('expedientes', 'Machote')
    Machote.objects.filter(archivo_origen=ARCHIVO_ORIGEN).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('expedientes', '0044_cliente_descripcion_hechos'),
    ]

    operations = [
        migrations.RunPython(crear_machote, eliminar_machote),
    ]
