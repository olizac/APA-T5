"""
Name: Oliwia Zacharska

Functions for handling stereo audio signals in WAVE files:
channel separation, merging, and stereo encoding/decoding
using the semi-sum and semi-difference scheme.
"""

import struct


def _lee_cabecera(f):
    """
    Read and validate the header of a WAVE PCM file.

    Args:
        f: An open binary file object.

    Returns:
        A tuple (canales, frec_muestreo, bits, num_muestras).
    """
    if f.read(4) != b'RIFF':
        raise Exception('Not a valid RIFF file.')
    f.read(4)
    if f.read(4) != b'WAVE':
        raise Exception('Not a valid WAVE file.')
    if f.read(4) != b'fmt ':
        raise Exception('Missing fmt chunk.')

    fmt_size = struct.unpack('<I', f.read(4))[0]
    fmt_data = f.read(fmt_size)
    audio_fmt, canales, frec_muestreo, _, _, bits = struct.unpack('<HHIIHH', fmt_data)

    if audio_fmt != 1:
        raise Exception('Not linear PCM.')
    if f.read(4) != b'data':
        raise Exception('Missing data chunk.')

    data_size = struct.unpack('<I', f.read(4))[0]
    num_muestras = data_size // (canales * bits // 8)

    return canales, frec_muestreo, bits, num_muestras


def _escribe_cabecera(f, canales, frec_muestreo, bits, num_muestras):
    """
    Write a standard WAVE PCM header.

    Args:
        f: An open binary file object.
        canales: Number of channels.
        frec_muestreo: Sample rate in Hz.
        bits: Bits per sample.
        num_muestras: Number of samples per channel.

    Returns:
        None.
    """
    block_align = canales * bits // 8
    data_size = num_muestras * block_align

    f.write(b'RIFF')
    f.write(struct.pack('<I', 36 + data_size))
    f.write(b'WAVE')
    f.write(b'fmt ')
    f.write(struct.pack('<I', 16))
    f.write(struct.pack('<HHIIHH', 1, canales, frec_muestreo,
                        frec_muestreo * block_align, block_align, bits))
    f.write(b'data')
    f.write(struct.pack('<I', data_size))


def estereo2mono(ficEste, ficMono, canal=2):
    """
    Convert a stereo WAVE file to mono.

    Args:
        ficEste: Path to the input stereo WAVE file.
        ficMono: Path to the output mono WAVE file.
        canal: 0 for L, 1 for R, 2 for (L+R)/2 (default), 3 for (L-R)/2.

    Returns:
        None.
    """
    with open(ficEste, 'rb') as f_in:
        canales, frec_muestreo, bits, num_muestras = _lee_cabecera(f_in)

        if canales != 2:
            raise Exception('Input file is not stereo.')
        if bits != 16:
            raise Exception('Input file is not 16-bit.')

        datos = struct.unpack(f'<{2 * num_muestras}h', f_in.read(2 * num_muestras * 2))

    muestras_l = datos[0::2]
    muestras_r = datos[1::2]

    if canal == 0:
        mono = muestras_l
    elif canal == 1:
        mono = muestras_r
    elif canal == 2:
        mono = tuple((l + r) // 2 for l, r in zip(muestras_l, muestras_r))
    elif canal == 3:
        mono = tuple((l - r) // 2 for l, r in zip(muestras_l, muestras_r))
    else:
        raise Exception('canal must be 0, 1, 2 or 3.')

    with open(ficMono, 'wb') as f_out:
        _escribe_cabecera(f_out, 1, frec_muestreo, 16, num_muestras)
        f_out.write(struct.pack(f'<{num_muestras}h', *mono))


def mono2estereo(ficIzq, ficDer, ficEste):
    """
    Combine two mono WAVE files into a stereo WAVE file.

    Args:
        ficIzq: Path to the left channel mono WAVE file.
        ficDer: Path to the right channel mono WAVE file.
        ficEste: Path to the output stereo WAVE file.

    Returns:
        None.
    """
    with open(ficIzq, 'rb') as f_l:
        canales_l, frec_l, bits_l, num_muestras_l = _lee_cabecera(f_l)
        if canales_l != 1:
            raise Exception('Left file is not mono.')
        if bits_l != 16:
            raise Exception('Left file is not 16-bit.')
        datos_l = struct.unpack(f'<{num_muestras_l}h', f_l.read(num_muestras_l * 2))

    with open(ficDer, 'rb') as f_r:
        canales_r, frec_r, bits_r, num_muestras_r = _lee_cabecera(f_r)
        if canales_r != 1:
            raise Exception('Right file is not mono.')
        if bits_r != 16:
            raise Exception('Right file is not 16-bit.')
        datos_r = struct.unpack(f'<{num_muestras_r}h', f_r.read(num_muestras_r * 2))

    if frec_l != frec_r:
        raise Exception('Sample rates do not match.')
    if num_muestras_l != num_muestras_r:
        raise Exception('Files have different number of samples.')

    estereo = [muestra for par in zip(datos_l, datos_r) for muestra in par]

    with open(ficEste, 'wb') as f_out:
        _escribe_cabecera(f_out, 2, frec_l, 16, num_muestras_l)
        f_out.write(struct.pack(f'<{2 * num_muestras_l}h', *estereo))


def codEstereo(ficEste, ficCod):
    """
    Encode a stereo 16-bit WAVE file into a mono 32-bit WAVE file.

    The 16 most significant bits store (L+R)/2 and the 16 least
    significant bits store (L-R)/2.

    Args:
        ficEste: Path to the input stereo 16-bit WAVE file.
        ficCod: Path to the output mono 32-bit WAVE file.

    Returns:
        None.
    """
    with open(ficEste, 'rb') as f_in:
        canales, frec_muestreo, bits, num_muestras = _lee_cabecera(f_in)

        if canales != 2:
            raise Exception('Input file is not stereo.')
        if bits != 16:
            raise Exception('Input file is not 16-bit.')

        datos = struct.unpack(f'<{2 * num_muestras}h', f_in.read(2 * num_muestras * 2))

    muestras_l = datos[0::2]
    muestras_r = datos[1::2]

    codificadas = [
        (((l + r) // 2) & 0xFFFF) << 16 | (((l - r) // 2) & 0xFFFF)
        for l, r in zip(muestras_l, muestras_r)
    ]

    with open(ficCod, 'wb') as f_out:
        _escribe_cabecera(f_out, 1, frec_muestreo, 32, num_muestras)
        f_out.write(struct.pack(f'<{num_muestras}I', *codificadas))


def decEstereo(ficCod, ficEste):
    """
    Decode a mono 32-bit WAVE file back into a stereo 16-bit WAVE file.

    The 16 most significant bits are interpreted as (L+R)/2 and the 16
    least significant bits as (L-R)/2. L and R are reconstructed as:
        L = semi-sum + semi-difference
        R = semi-sum - semi-difference

    Args:
        ficCod: Path to the input mono 32-bit WAVE file.
        ficEste: Path to the output stereo 16-bit WAVE file.

    Returns:
        None.
    """
    with open(ficCod, 'rb') as f_in:
        canales, frec_muestreo, bits, num_muestras = _lee_cabecera(f_in)

        if canales != 1:
            raise Exception('Input file is not mono.')
        if bits != 32:
            raise Exception('Input file is not 32-bit.')

        datos = struct.unpack(f'<{num_muestras}I', f_in.read(num_muestras * 4))

    def _semisuma(muestra):
        return struct.unpack('<h', struct.pack('<H', (muestra >> 16) & 0xFFFF))[0]

    def _semidif(muestra):
        return struct.unpack('<h', struct.pack('<H', muestra & 0xFFFF))[0]

    estereo = [
        canal
        for muestra in datos
        for canal in (_semisuma(muestra) + _semidif(muestra),
                      _semisuma(muestra) - _semidif(muestra))
    ]

    with open(ficEste, 'wb') as f_out:
        _escribe_cabecera(f_out, 2, frec_muestreo, 16, num_muestras)
        f_out.write(struct.pack(f'<{2 * num_muestras}h', *estereo))