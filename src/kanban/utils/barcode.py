"""
Code128 barcode generation in pure Python.
Generates SVG barcodes without external dependencies.
"""

# Code128 character set B (most common for alphanumeric)
CODE128_B = {
    ' ': 0, '!': 1, '"': 2, '#': 3, '$': 4, '%': 5, '&': 6, "'": 7,
    '(': 8, ')': 9, '*': 10, '+': 11, ',': 12, '-': 13, '.': 14, '/': 15,
    '0': 16, '1': 17, '2': 18, '3': 19, '4': 20, '5': 21, '6': 22, '7': 23,
    '8': 24, '9': 25, ':': 26, ';': 27, '<': 28, '=': 29, '>': 30, '?': 31,
    '@': 32, 'A': 33, 'B': 34, 'C': 35, 'D': 36, 'E': 37, 'F': 38, 'G': 39,
    'H': 40, 'I': 41, 'J': 42, 'K': 43, 'L': 44, 'M': 45, 'N': 46, 'O': 47,
    'P': 48, 'Q': 49, 'R': 50, 'S': 51, 'T': 52, 'U': 53, 'V': 54, 'W': 55,
    'X': 56, 'Y': 57, 'Z': 58, '[': 59, '\\': 60, ']': 61, '^': 62, '_': 63,
    '`': 64, 'a': 65, 'b': 66, 'c': 67, 'd': 68, 'e': 69, 'f': 70, 'g': 71,
    'h': 72, 'i': 73, 'j': 74, 'k': 75, 'l': 76, 'm': 77, 'n': 78, 'o': 79,
    'p': 80, 'q': 81, 'r': 82, 's': 83, 't': 84, 'u': 85, 'v': 86, 'w': 87,
    'x': 88, 'y': 89, 'z': 90, '{': 91, '|': 92, '}': 93, '~': 94,
}

# Bar patterns for Code128 (BSBSBS format: bars and spaces)
PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
    "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
    "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
    "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
    "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
    "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
    "211214", "211232", "2331112",  # Last one is stop pattern
]

START_B = 104
STOP = 106


def encode_code128(text: str) -> list[int]:
    """Encode text to Code128 code values."""
    if not text:
        raise ValueError("Text cannot be empty")
    
    codes = [START_B]
    
    for char in text:
        if char not in CODE128_B:
            raise ValueError(f"Character '{char}' not supported in Code128B")
        codes.append(CODE128_B[char])
    
    # Calculate checksum
    checksum = START_B
    for i, code in enumerate(codes[1:], 1):
        checksum += i * code
    checksum = checksum % 103
    codes.append(checksum)
    codes.append(STOP)
    
    return codes


def codes_to_bars(codes: list[int]) -> str:
    """Convert code values to bar pattern string."""
    bars = ""
    for code in codes:
        bars += PATTERNS[code]
    return bars


def generate_code128_svg(text: str, height: int = 50, module_width: int = 2) -> str:
    """
    Generate an SVG barcode for the given text.
    
    Args:
        text: The text to encode
        height: Height of the barcode in pixels
        module_width: Width of the narrowest bar in pixels
    
    Returns:
        SVG string
    """
    codes = encode_code128(text)
    bars = codes_to_bars(codes)
    
    # Calculate total width
    total_modules = sum(int(b) for b in bars)
    width = total_modules * module_width + 20  # Add quiet zones
    
    # Build SVG
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    ]
    
    x = 10  # Start with quiet zone
    is_bar = True
    
    for char in bars:
        modules = int(char)
        bar_width = modules * module_width
        
        if is_bar:
            svg_parts.append(
                f'<rect x="{x}" y="0" width="{bar_width}" height="{height}" fill="black"/>'
            )
        
        x += bar_width
        is_bar = not is_bar
    
    svg_parts.append('</svg>')
    
    return ''.join(svg_parts)

