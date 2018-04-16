# coding: utf-8

import numpy as np
from PIL import Image


def histeq_func(img):
    hist, bins = np.histogram(img.flatten(), bins=256)
    cdf = hist.cumsum()
    add = max(img.std()-np.arange(255).std(), 0)
    cdf = (255+add*4) * cdf / cdf[-1]
    img2 = np.interp( img.flatten(), bins[:-1], cdf)
    img2[img2>255] = 255
    img2[img2<0] = 0
    img2 = img2.reshape(img.shape).astype(np.uint8)
    return img2


def _prepare_colorarray(arr):
    arr = np.asanyarray(arr)
    return arr.astype(np.float32)


def rgb2hsv(rgb):
    arr = _prepare_colorarray(rgb)
    out = np.empty_like(arr)

    # -- V channel
    out_v = arr.max(-1)

    # -- S channel
    delta = arr.ptp(-1)
    # Ignore warning for zero divided by zero
    old_settings = np.seterr(invalid='ignore')
    out_s = delta / out_v
    out_s[delta == 0.] = 0.

    # -- H channel
    # red is max
    idx = (arr[:, :, 0] == out_v)
    out[idx, 0] = (arr[idx, 1] - arr[idx, 2]) / delta[idx]

    # green is max
    idx = (arr[:, :, 1] == out_v)
    out[idx, 0] = 2. + (arr[idx, 2] - arr[idx, 0]) / delta[idx]

    # blue is max
    idx = (arr[:, :, 2] == out_v)
    out[idx, 0] = 4. + (arr[idx, 0] - arr[idx, 1]) / delta[idx]
    out_h = (out[:, :, 0] / 6.) % 1.
    out_h[delta == 0.] = 0.

    np.seterr(**old_settings)

    # -- output
    out[:, :, 0] = out_h
    out[:, :, 1] = out_s
    out[:, :, 2] = out_v

    # remove NaN
    out[np.isnan(out)] = 0

    return out


def hsv2rgb(hsv):
    arr = _prepare_colorarray(hsv)

    hi = np.floor(arr[:, :, 0] * 6)
    f = arr[:, :, 0] * 6 - hi
    p = arr[:, :, 2] * (1 - arr[:, :, 1])
    q = arr[:, :, 2] * (1 - f * arr[:, :, 1])
    t = arr[:, :, 2] * (1 - (1 - f) * arr[:, :, 1])
    v = arr[:, :, 2]

    hi = np.dstack([hi, hi, hi]).astype(np.uint8) % 6
    out = np.choose(hi, [np.dstack((v, t, p)),
                         np.dstack((q, v, p)),
                         np.dstack((p, v, t)),
                         np.dstack((p, q, v)),
                         np.dstack((t, p, v)),
                         np.dstack((v, p, q))])

    out = out.astype(np.uint8)
    return out


def histeq_main(img):

    hsv = rgb2hsv(img)

    v = hsv[:,:,2].astype(np.uint8)
    if np.mean(v) > 127:
        vo = histeq_func(v)
    else:
        vo = 255 - histeq_func(255-v)
    hsv[:,:,2] = vo.astype(np.float32)

    return hsv2rgb(hsv)
