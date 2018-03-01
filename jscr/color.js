/*
 * Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc., 51
 * Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 */

com.sweattrails.api.UnknownColor = function(c) {
  this.message = "Unknown color representation " + c;  
};

com.sweattrails.api.Color = function(c) {
    if ((arguments.length === 3) || (arguments.length === 4)) {
        this.red = parseInt(arguments[0]);
        this.green = parseInt(arguments[1]);
        this.blue = parseInt(arguments[2]);
        this.alpha = ((arguments.length === 4) && !isNaN(arguments[3])) ? parseFloat(arguments[3]) : NaN;
    } else if (arguments.length === 0) {
        this.red = this.green = this.blue = 0;
        this.alpha = NaN;
    } else if (arguments.length !== 1) {
        throw new com.sweattrails.api.UnknownColor(arguments);
    } else if (typeof(c) === "string") {
        c = c.toLowerCase();
        if ((c[0].slice(0,4) !== 'rgb(') && (c[0] !== '#')) {
            if (com.sweattrails.api.HTMLColors[c]) {
                com.sweattrails.api.Color.bind(this)(com.sweattrails.api.HTMLColors[c]);
            } else {
                throw new com.sweattrails.api.UnknownColor(c);
            }
        } else {
            var l = c.length;
            var d;
            if (l > 9) {
                d = c.split(",");
                if ((d.length < 3) || (d.length > 4)) {
                    throw com.sweattrails.api.UnknownColor(c);
                }
                if (d[0][0] === 'r') {
                    d[0] = d[0].slice(4);
                }
                var last = d[d.length - 1];
                if (last[last.length - 1] === ')') {
                    d[d.length - 1] = last.slice(0, last.length - 1);
                }
                if (d.length === 3) {
                    com.sweattrails.api.Color.bind(this)(d[0], d[1], d[2]);
                } else if (d.length === 4) {
                    com.sweattrails.api.Color.bind(this)(d[0], d[1], d[2], d[3]);
                }
            } else {
                if ((l === 8) || (l === 6) || (l < 4)) {
                    throw new com.sweattrails.api.UnknownColor(c);
                }
                if (l < 6) {  //3 digit
                    c = "#" + c[1] + c[1] + c[2] + c[2] + c[3] + c[3] + ((l > 4) ? (c[4] + "" + c[4]) : "");
                }
                d = parseInt(c.slice(1), 16);
                this.red = (d >> 16) & 255;
                this.green = (d >> 8) & 255;
                this.blue = d & 255;
                this.alpha = ((l === 9) || (l === 5)) ? Math.round(((d >> 24 & 255) / 255) * 10000) / 10000 : NaN;
            }
        }
    } else if ((typeof(c.red) !== "undefined") &&
               (typeof(c.green) !== "undefined") &&
               (typeof(c.blue) !== "undefined")) {
        this.red = parseInt(c.red);
        this.green = parseInt(c.green);
        this.blue = parseInt(c.blue);
        this.alpha = (typeof(c.alpha) !== "undefined" && !isNaN(c.alpha)) ? parseFloat(c.alpha) : NaN;
    } else if (Array.isArray(c)) {
        if (c.length === 3) {
            com.sweattrails.api.Color.bind(this)(c[0], c[1], c[2]);
        } else if (c.length === 4) {
            com.sweattrails.api.Color.bind(this)(c[0], c[1], c[2], c[3]);
        } else {
            throw com.sweattrails.api.UnknownColor(c);
        }
    } else {
        throw new com.sweattrails.api.UnknownColor(c);
    }
};

com.sweattrails.api.Color.prototype.rgb = function() {
    var ret = "rgb(" + this.red + "," + this.green + "," + this.blue;
    if (!isNaN(this.alpha)) {
        ret += "," + this.alpha;
    }
    ret += ")";
    return ret;
};

com.sweattrails.api.Color.prototype.hex = function() {
    var alpha = (!isNaN(this.alpha) && (this.alpha > 0))
        ? Math.round(this.alpha * 255) << 24
        : 0;
    var n = parseInt(alpha + (this.red << 16) + (this.green << 8) + this.blue).toString(16);
    if (n.length % 2) {
        n = "0" + n;
    }
    return "#" + n;
};

/*
 * http://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
 *
 *
 *
 * var color1 = "rgb(114,93,20)";
 * var color2 = "rgb(114,93,20,0.37423)";
 * var color3 = "#67DAF0";
 * var color4 = "#5567DAF0";
 * var color5 = "#F3A";
 * var color6 = "#DF3A";
 * var color7 = "rgb(75,200,112)";
 * var color8 = "rgb(75,200,112,0.98631)";
 * var c;
 *
 * // Shade (Lighten or Darken)
 * c = shadeBlendConvert(0.3,color1); // rgb(114,93,20) + [30% Lighter] => rgb(156,142,91)
 * c = shadeBlendConvert(-0.13,color5); // #F3A + [13% Darker]  => #de2c94
 * // Shade with Conversion (use 'c' as your 'to' color)
 * c = shadeBlendConvert(0.42,color2,"c"); //rgb(114,93,20,0.37423) + [42% Lighter] + [Convert] => #5fada177
 * // RGB2Hex & Hex2RGB Conversion Only (set percentage to zero)
 * c = shadeBlendConvert(0,color6,"c"); // #DF3A + [Convert] => rgb(255,51,170,0.8667)
 * // Blending
 * c = shadeBlendConvert(-0.13,color2,color8); // rgb(114,93,20,0.37423) + rgb(75,200,112,0.98631) + [13% Blend] => rgb(109,107,32,0.4538)
 * c = shadeBlendConvert(0.65,color2,color7); // rgb(114,93,20,0.37423) + rgb(75,200,112) + [65% Blend] => rgb(89,163,80,0.37423)
 * // Blending with Conversion  (result is in the 'to' color format)
 * c = shadeBlendConvert(0.3,color1,color3); // rgb(114,93,20) + #67DAF0 + [30% Blend] + [Convert] => #6f8356
 * c = shadeBlendConvert(-0.13,color4,color2); // #5567DAF0 + rgb(114,93,20,0.37423) + [13% Blend] + [Convert] => rgb(104,202,211,0.3386)
 * // Error Checking
 * c = shadeBlendConvert(0.3,"#FFBAA"); // #FFBAA + [30% Lighter] => null
 * c = shadeBlendConvert(30,color1,color5); // rgb(114,93,20) + #F3A + [3000% Blend] => null
 * // A pound of salt is jibberish  (Error Check Fail)
 * c = shadeBlendConvert(0.3,"#salt");  // #salt + [30% Lighter] => #004d4d4d
 */
com.sweattrails.api.Color.prototype.shadeBlend = function(p) {
    if ((p < -1) || (p > 1)) {
        return null;
    }
    var darker = p < 0;
    p = darker ? p * -1 : p;
    var t = (arguments.length > 1)
            ? __.getColor(arguments[1])
            : ((darker) ? __.HTMLColors.black : __.HTMLColors.white);
    var c = {
        red: Math.round((t.red - this.red) * p + this.red),
        green: Math.round((t.green - this.green) * p + this.green),
        blue: Math.round((t.blue - this.blue) * p + this.blue)
    };
    if (!isNaN(this.alpha) && !isNaN(t.alpha)) {
        c.alpha = Math.round(((t.alpha - this.alpha) * p + this.alpha) * 10000) / 10000;
    } else if (!isNaN(t.alpha)) {
        c.alpha = t.alpha;
    } else if (!isNaN(this.alpha)) {
        c.alpha = this.alpha;
    }
    return new com.sweattrails.api.Color(c);
};

com.sweattrails.api.Color.prototype.shade = function(factor) {
    return this.shadeBlend(factor);
};

com.sweattrails.api.Color.prototype.blend = function(blendTo) {
    return this.shadeBlend(1.0, blendTo);
};

com.sweattrails.api.HTMLColors = {
    aliceblue:            new com.sweattrails.api.Color(0xf0, 0xf8, 0xff),
    antiquewhite:         new com.sweattrails.api.Color(0xfa, 0xeb, 0xd7),
    aqua:                 new com.sweattrails.api.Color(0x00, 0xff, 0xff),
    aquamarine:           new com.sweattrails.api.Color(0x7f, 0xff, 0xd4),
    azure:                new com.sweattrails.api.Color(0xf0, 0xff, 0xff),
    beige:                new com.sweattrails.api.Color(0xf5, 0xf5, 0xdc),
    bisque:               new com.sweattrails.api.Color(0xff, 0xe4, 0xc4),
    black:                new com.sweattrails.api.Color(0x00, 0x00, 0x00),
    blanchedalmond:       new com.sweattrails.api.Color(0xff, 0xeb, 0xcd),
    blue:                 new com.sweattrails.api.Color(0x00, 0x00, 0xff),
    blueviolet:           new com.sweattrails.api.Color(0x8a, 0x2b, 0xe2),
    brown:                new com.sweattrails.api.Color(0xa5, 0x2a, 0x2a),
    burlywood:            new com.sweattrails.api.Color(0xde, 0xb8, 0x87),
    cadetblue:            new com.sweattrails.api.Color(0x5f, 0x9e, 0xa0),
    chartreuse:           new com.sweattrails.api.Color(0x7f, 0xff, 0x00),
    chocolate:            new com.sweattrails.api.Color(0xd2, 0x69, 0x1e),
    coral:                new com.sweattrails.api.Color(0xff, 0x7f, 0x50),
    cornflowerblue:       new com.sweattrails.api.Color(0x64, 0x95, 0xed),
    cornsilk:             new com.sweattrails.api.Color(0xff, 0xf8, 0xdc),
    crimson:              new com.sweattrails.api.Color(0xdc, 0x14, 0x3c),
    cyan:                 new com.sweattrails.api.Color(0x00, 0xff, 0xff),
    darkblue:             new com.sweattrails.api.Color(0x00, 0x00, 0x8b),
    darkcyan:             new com.sweattrails.api.Color(0x00, 0x8b, 0x8b),
    darkgoldenrod:        new com.sweattrails.api.Color(0xb8, 0x86, 0x0b),
    darkgray:             new com.sweattrails.api.Color(0xa9, 0xa9, 0xa9),
    darkgrey:             new com.sweattrails.api.Color(0xa9, 0xa9, 0xa9),
    darkgreen:            new com.sweattrails.api.Color(0x00, 0x64, 0x00),
    darkkhaki:            new com.sweattrails.api.Color(0xbd, 0xb7, 0x6b),
    darkmagenta:          new com.sweattrails.api.Color(0x8b, 0x00, 0x8b),
    darkolivegreen:       new com.sweattrails.api.Color(0x55, 0x6b, 0x2f),
    darkorange:           new com.sweattrails.api.Color(0xff, 0x8c, 0x00),
    darkorchid:           new com.sweattrails.api.Color(0x99, 0x32, 0xcc),
    darkred:              new com.sweattrails.api.Color(0x8b, 0x00, 0x00),
    darksalmon:           new com.sweattrails.api.Color(0xe9, 0x96, 0x7a),
    darkseagreen:         new com.sweattrails.api.Color(0x8f, 0xbc, 0x8f),
    darkslateblue:        new com.sweattrails.api.Color(0x48, 0x3d, 0x8b),
    darkslategray:        new com.sweattrails.api.Color(0x2f, 0x4f, 0x4f),
    darkslategrey:        new com.sweattrails.api.Color(0x2f, 0x4f, 0x4f),
    darkturquoise:        new com.sweattrails.api.Color(0x00, 0xce, 0xd1),
    darkviolet:           new com.sweattrails.api.Color(0x94, 0x00, 0xd3),
    deeppink:             new com.sweattrails.api.Color(0xff, 0x14, 0x93),
    deepskyblue:          new com.sweattrails.api.Color(0x00, 0xbf, 0xff),
    dimgray:              new com.sweattrails.api.Color(0x69, 0x69, 0x69),
    dimgrey:              new com.sweattrails.api.Color(0x69, 0x69, 0x69),
    dodgerblue:           new com.sweattrails.api.Color(0x1e, 0x90, 0xff),
    firebrick:            new com.sweattrails.api.Color(0xb2, 0x22, 0x22),
    floralwhite:          new com.sweattrails.api.Color(0xff, 0xfa, 0xf0),
    forestgreen:          new com.sweattrails.api.Color(0x22, 0x8b, 0x22),
    fuchsia:              new com.sweattrails.api.Color(0xff, 0x00, 0xff),
    gainsboro:            new com.sweattrails.api.Color(0xdc, 0xdc, 0xdc),
    ghostwhite:           new com.sweattrails.api.Color(0xf8, 0xf8, 0xff),
    gold:                 new com.sweattrails.api.Color(0xff, 0xd7, 0x00),
    goldenrod:            new com.sweattrails.api.Color(0xda, 0xa5, 0x20),
    gray:                 new com.sweattrails.api.Color(0x80, 0x80, 0x80),
    grey:                 new com.sweattrails.api.Color(0x80, 0x80, 0x80),
    green:                new com.sweattrails.api.Color(0x00, 0x80, 0x00),
    greenyellow:          new com.sweattrails.api.Color(0xad, 0xff, 0x2f),
    honeydew:             new com.sweattrails.api.Color(0xf0, 0xff, 0xf0),
    hotpink:              new com.sweattrails.api.Color(0xff, 0x69, 0xb4),
    indianred :           new com.sweattrails.api.Color(0xcd, 0x5c, 0x5c),
    indigo:               new com.sweattrails.api.Color(0x4b, 0x00, 0x82),
    ivory:                new com.sweattrails.api.Color(0xff, 0xff, 0xf0),
    khaki:                new com.sweattrails.api.Color(0xf0, 0xe6, 0x8c),
    lavender:             new com.sweattrails.api.Color(0xe6, 0xe6, 0xfa),
    lavenderblush:        new com.sweattrails.api.Color(0xff, 0xf0, 0xf5),
    lawngreen:            new com.sweattrails.api.Color(0x7c, 0xfc, 0x00),
    lemonchiffon:         new com.sweattrails.api.Color(0xff, 0xfa, 0xcd),
    lightblue:            new com.sweattrails.api.Color(0xad, 0xd8, 0xe6),
    lightcoral:           new com.sweattrails.api.Color(0xf0, 0x80, 0x80),
    lightcyan:            new com.sweattrails.api.Color(0xe0, 0xff, 0xff),
    lightgoldenrodyellow: new com.sweattrails.api.Color(0xfa, 0xfa, 0xd2),
    lightgray:            new com.sweattrails.api.Color(0xd3, 0xd3, 0xd3),
    lightgrey:            new com.sweattrails.api.Color(0xd3, 0xd3, 0xd3),
    lightgreen:           new com.sweattrails.api.Color(0x90, 0xee, 0x90),
    lightpink:            new com.sweattrails.api.Color(0xff, 0xb6, 0xc1),
    lightsalmon:          new com.sweattrails.api.Color(0xff, 0xa0, 0x7a),
    lightseagreen:        new com.sweattrails.api.Color(0x20, 0xb2, 0xaa),
    lightskyblue:         new com.sweattrails.api.Color(0x87, 0xce, 0xfa),
    lightslategray:       new com.sweattrails.api.Color(0x77, 0x88, 0x99),
    lightslategrey:       new com.sweattrails.api.Color(0x77, 0x88, 0x99),
    lightsteelblue:       new com.sweattrails.api.Color(0xb0, 0xc4, 0xde),
    lightyellow:          new com.sweattrails.api.Color(0xff, 0xff, 0xe0),
    lime:                 new com.sweattrails.api.Color(0x00, 0xff, 0x00),
    limegreen:            new com.sweattrails.api.Color(0x32, 0xcd, 0x32),
    linen:                new com.sweattrails.api.Color(0xfa, 0xf0, 0xe6),
    magenta:              new com.sweattrails.api.Color(0xff, 0x00, 0xff),
    maroon:               new com.sweattrails.api.Color(0x80, 0x00, 0x00),
    mediumaquamarine:     new com.sweattrails.api.Color(0x66, 0xcd, 0xaa),
    mediumblue:           new com.sweattrails.api.Color(0x00, 0x00, 0xcd),
    mediumorchid:         new com.sweattrails.api.Color(0xba, 0x55, 0xd3),
    mediumpurple:         new com.sweattrails.api.Color(0x93, 0x70, 0xdb),
    mediumseagreen:       new com.sweattrails.api.Color(0x3c, 0xb3, 0x71),
    mediumslateblue:      new com.sweattrails.api.Color(0x7b, 0x68, 0xee),
    mediumspringgreen:    new com.sweattrails.api.Color(0x00, 0xfa, 0x9a),
    mediumturquoise:      new com.sweattrails.api.Color(0x48, 0xd1, 0xcc),
    mediumvioletred:      new com.sweattrails.api.Color(0xc7, 0x15, 0x85),
    midnightblue:         new com.sweattrails.api.Color(0x19, 0x19, 0x70),
    mintcream:            new com.sweattrails.api.Color(0xf5, 0xff, 0xfa),
    mistyrose:            new com.sweattrails.api.Color(0xff, 0xe4, 0xe1),
    moccasin:             new com.sweattrails.api.Color(0xff, 0xe4, 0xb5),
    navajowhite:          new com.sweattrails.api.Color(0xff, 0xde, 0xad),
    navy:                 new com.sweattrails.api.Color(0x00, 0x00, 0x80),
    oldlace:              new com.sweattrails.api.Color(0xfd, 0xf5, 0xe6),
    olive:                new com.sweattrails.api.Color(0x80, 0x80, 0x00),
    olivedrab:            new com.sweattrails.api.Color(0x6b, 0x8e, 0x23),
    orange:               new com.sweattrails.api.Color(0xff, 0xa5, 0x00),
    orangered:            new com.sweattrails.api.Color(0xff, 0x45, 0x00),
    orchid:               new com.sweattrails.api.Color(0xda, 0x70, 0xd6),
    palegoldenrod:        new com.sweattrails.api.Color(0xee, 0xe8, 0xaa),
    palegreen:            new com.sweattrails.api.Color(0x98, 0xfb, 0x98),
    paleturquoise:        new com.sweattrails.api.Color(0xaf, 0xee, 0xee),
    palevioletred:        new com.sweattrails.api.Color(0xdb, 0x70, 0x93),
    papayawhip:           new com.sweattrails.api.Color(0xff, 0xef, 0xd5),
    peachpuff:            new com.sweattrails.api.Color(0xff, 0xda, 0xb9),
    peru:                 new com.sweattrails.api.Color(0xcd, 0x85, 0x3f),
    pink:                 new com.sweattrails.api.Color(0xff, 0xc0, 0xcb),
    plum:                 new com.sweattrails.api.Color(0xdd, 0xa0, 0xdd),
    powderblue:           new com.sweattrails.api.Color(0xb0, 0xe0, 0xe6),
    purple:               new com.sweattrails.api.Color(0x80, 0x00, 0x80),
    rebeccapurple:        new com.sweattrails.api.Color(0x66, 0x33, 0x99),
    red:                  new com.sweattrails.api.Color(0xff, 0x00, 0x00),
    rosybrown:            new com.sweattrails.api.Color(0xbc, 0x8f, 0x8f),
    royalblue:            new com.sweattrails.api.Color(0x41, 0x69, 0xe1),
    saddlebrown:          new com.sweattrails.api.Color(0x8b, 0x45, 0x13),
    salmon:               new com.sweattrails.api.Color(0xfa, 0x80, 0x72),
    sandybrown:           new com.sweattrails.api.Color(0xf4, 0xa4, 0x60),
    seagreen:             new com.sweattrails.api.Color(0x2e, 0x8b, 0x57),
    seashell:             new com.sweattrails.api.Color(0xff, 0xf5, 0xee),
    sienna:               new com.sweattrails.api.Color(0xa0, 0x52, 0x2d),
    silver:               new com.sweattrails.api.Color(0xc0, 0xc0, 0xc0),
    skyblue:              new com.sweattrails.api.Color(0x87, 0xce, 0xeb),
    slateblue:            new com.sweattrails.api.Color(0x6a, 0x5a, 0xcd),
    slategray:            new com.sweattrails.api.Color(0x70, 0x80, 0x90),
    slategrey:            new com.sweattrails.api.Color(0x70, 0x80, 0x90),
    snow:                 new com.sweattrails.api.Color(0xff, 0xfa, 0xfa),
    springgreen:          new com.sweattrails.api.Color(0x00, 0xff, 0x7f),
    steelblue:            new com.sweattrails.api.Color(0x46, 0x82, 0xb4),
    tan:                  new com.sweattrails.api.Color(0xd2, 0xb4, 0x8c),
    teal:                 new com.sweattrails.api.Color(0x00, 0x80, 0x80),
    thistle:              new com.sweattrails.api.Color(0xd8, 0xbf, 0xd8),
    tomato:               new com.sweattrails.api.Color(0xff, 0x63, 0x47),
    turquoise:            new com.sweattrails.api.Color(0x40, 0xe0, 0xd0),
    violet:               new com.sweattrails.api.Color(0xee, 0x82, 0xee),
    wheat:                new com.sweattrails.api.Color(0xf5, 0xde, 0xb3),
    white:                new com.sweattrails.api.Color(0xff, 0xff, 0xff),
    whitesmoke:           new com.sweattrails.api.Color(0xf5, 0xf5, 0xf5),
    yellow:               new com.sweattrails.api.Color(0xff, 0xff, 0x00),
    yellowgreen:          new com.sweattrails.api.Color(0x9a, 0xcd, 0x32)
};

com.sweattrails.api.getColor = function(c) {
    if (typeof(c) === "string") {
        c = c.toLowerCase();
        if (com.sweattrails.api.HTMLColors[c]) {
            return com.sweattrails.api.HTMLColors[c];
        }
    } else if (c.__proto__ === com.sweattrails.api.Color.prototype) {
        return c;
    }
    return new com.sweattrails.api.Color(c);
};

