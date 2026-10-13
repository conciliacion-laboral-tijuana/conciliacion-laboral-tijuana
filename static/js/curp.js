/**
 * Generador de CURP — algoritmo oficial RENAPO/SAT (compartido por la página
 * /curp/ y el modal de base.html).
 * Implementación basada en la librería verificada 'curp' (npm) que
 * reproduce CURP reales (ej. AMLO: LOOA531113HTCPBN07).
 *
 * Estructura:
 *   [1-4]  Letras (apellido paterno, vocal interna, apellido materno, nombre)
 *   [5-10] Fecha de nacimiento YYMMDD
 *   [11]   Sexo (H/M/X)
 *   [12-13] Entidad federativa (catálogo oficial)
 *   [14-16] Consonantes internas
 *   [17]   Homoclave — la ASIGNA RENAPO aleatoriamente; aquí se usa el
 *          carácter por defecto según el año (0 si <2000, A si >=2000)
 *   [18]   Dígito verificador (Σ índice×(18−i) mod 10)
 */
(function (global) {
    const DICCIONARIO = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ';

    // Partículas que se eliminan de nombres/apellidos compuestos
    const PARTICULAS = /\b(DA|DAS|DE|DEL|DER|DI|DIE|DD|EL|LA|LOS|LAS|LE|LES|MAC|MC|VAN|VON|Y)\b/g;

    // Nombres comunes que se omiten como primer nombre (María/José, etc.)
    const NOMBRES_COMUNES = ['MARIA DEL ','MARIA DE LOS ','MARIA ','JOSE DE ','JOSE ','MA. ','MA ','M. ','J. ','J ','M '];

    // Palabras inconvenientes: la 2ª letra se sustituye por X (regla oficial RENAPO)
    const MALAS_PALABRAS = {
        'BACA':'BXCA','BAKA':'BXKA','BUEI':'BXEI','BUEY':'BXEY','CACA':'CXCA','CACO':'CXCO',
        'CAGA':'CXGA','CAGO':'CXGO','CAKA':'CXKA','CAKO':'CXKO','COGE':'CXGE','COGI':'CXGI',
        'COJA':'CXJA','COJE':'CXJE','COJI':'CXJI','COJO':'CXJO','COLA':'CXLA','CULO':'CXLO',
        'FALO':'FXLO','FETO':'FXTO','GETA':'GXTA','GUEI':'GXEI','GUEY':'GXEY','JETA':'JXTA',
        'JOTO':'JXTO','KACA':'KXCA','KACO':'KXCO','KAGA':'KXGA','KAGO':'KXGO','KAKA':'KXKA',
        'KAKO':'KXKO','KOGE':'KXGE','KOGI':'KXGI','KOJA':'KXJA','KOJE':'KXJE','KOJI':'KXJI',
        'KOJO':'KXJO','KOLA':'KXLA','KULO':'KXLO','LILO':'LXLO','LOCA':'LXCA','LOCO':'LXCO',
        'LOKA':'LXKA','LOKO':'LXKO','MAME':'MXME','MAMO':'MXMO','MEAR':'MXAR','MEAS':'MXAS',
        'MEON':'MXON','MIAR':'MXAR','MION':'MXON','MOCO':'MXCO','MOKO':'MXKO','MULA':'MXLA',
        'MULO':'MXLO','NACA':'NXCA','NACO':'NXCO','PEDA':'PXDA','PEDO':'PXDO','PENE':'PXNE',
        'PIPI':'PXPI','PITO':'PXTO','POPO':'PXPO','PUTA':'PXTA','PUTO':'PXTO','QULO':'QXLO',
        'RATA':'RXTA','ROBA':'RXBA','ROBE':'RXBE','ROBO':'RXBO','RUIN':'RXIN','SENO':'SXNO',
        'TETA':'TXTA','VACA':'VXCA','VAGA':'VXGA','VAGO':'VXGO','VAKA':'VXKA','VUEI':'VXEI',
        'VUEY':'VXEY','WUEI':'WXEI','WUEY':'WXEY'
    };

    /** Elimina acentos conservando la Ñ (que luego se sustituye por X según reglas). */
    function normalizar(s) {
        s = (s || '').toUpperCase().replace(/Ñ/g, '\u0001'); // protege Ñ del NFD
        s = s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\u0001/g, 'Ñ');
        return s.trim().replace(/\s+/g, ' ');
    }

    /** Elimina partículas de los compuestos (DE, LA, DEL, MAC, VON, ...). */
    function ajustarCompuesto(s) {
        return (s || '').replace(PARTICULAS, ' ').replace(/\s+/g, ' ').trim();
    }

    /** Primer nombre útil (omite María/José cuando hay más nombres). */
    function obtenerNombreUsar(nombre) {
        const nombres = (nombre || '').trim().split(/\s+/);
        if (nombres.length === 1) return nombres[0];
        const esComun = NOMBRES_COMUNES.some(c => nombre.indexOf(c) === 0);
        return esComun ? nombres[1] : nombres[0];
    }

    /** Primera vocal interna (después de la 1ª letra). */
    function vocalInterna(s) {
        const resto = (s || '').substring(1).replace(/[^AEIOU]/g, '');
        return resto.substring(0, 1) || 'X';
    }

    /** Primera consonante interna (después de la 1ª letra); Ñ → X. */
    function consonanteInterna(s) {
        const resto = (s || '').substring(1).replace(/[^BCDFGHJKLMNÑPQRSTVWXYZ]/g, '');
        const c = resto.substring(0, 1);
        return (!c || c === 'Ñ') ? 'X' : c;
    }

    /** Letra inicial, con Ñ → X. */
    function inicial(s) {
        const c = (s || '').charAt(0);
        return c === 'Ñ' ? 'X' : (c || 'X');
    }

    /** Carácter de homoclave por defecto según el año de nacimiento. */
    function caracterHomoclave(anio) {
        return String(anio).charAt(0) === '1' ? '0' : 'A';
    }

    /** Dígito verificador oficial: Σ índice(carácter)×(18−i) para i=0..16, mod 10. */
    function digitoVerificador(curp17) {
        let suma = 0;
        for (let i = 0; i < 17; i++) {
            suma += DICCIONARIO.indexOf(curp17.charAt(i)) * (18 - i);
        }
        const digito = 10 - (suma % 10);
        return digito === 10 ? 0 : digito;
    }

    /**
     * Calcula la CURP. `fecha` en formato YYYY-MM-DD.
     * Devuelve { curp, letras, cons, error } — `error` es un mensaje si faltan
     * datos o son inválidos (curp = '' en ese caso).
     */
    function calcular({ apellido1, apellido2, nombres, fecha, sexo, estado }) {
        const ap1 = ajustarCompuesto(normalizar(apellido1));
        const ap2 = ajustarCompuesto(normalizar(apellido2));
        const nom = ajustarCompuesto(normalizar(nombres));

        if (!ap1 || !nom || !fecha || !sexo || !estado) return { curp: '', error: null };
        if (ap1.length < 2) return { curp: '', error: 'El apellido paterno debe tener al menos 2 letras.' };
        if (nom.length < 2) return { curp: '', error: 'El nombre debe tener al menos 2 letras.' };
        if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return { curp: '', error: 'Ingresa una fecha de nacimiento válida.' };

        // 4 primeras letras
        const nombreUsar = obtenerNombreUsar(nom);
        let letras = inicial(ap1) + vocalInterna(ap1) + inicial(ap2 || 'X') + inicial(nombreUsar);
        // Regla de palabras inconvenientes (2ª letra → X)
        if (MALAS_PALABRAS[letras]) letras = MALAS_PALABRAS[letras];

        const [anio, mes, dia] = fecha.split('-');

        // Consonantes internas
        const cons = consonanteInterna(ap1) + consonanteInterna(ap2) + consonanteInterna(nombreUsar);

        const curp17 = letras + anio.substring(2) + mes + dia + sexo + estado + cons + caracterHomoclave(anio);
        const curp = curp17 + digitoVerificador(curp17);
        if (curp.length !== 18) return { curp: '', error: 'No se pudo generar la CURP. Verifica los datos.' };

        return { curp, letras, cons, anio, mes, dia, error: null };
    }

    global.CURP = { calcular, digitoVerificador, normalizar };
})(window);
