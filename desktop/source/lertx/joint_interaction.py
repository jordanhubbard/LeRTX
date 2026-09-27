"""Portable coordinate and bounded joint-drag math. No device I/O."""
import math


def image_coordinates(x, y, rect):
    left, top, width, height = rect
    if width <= 0 or height <= 0 or not (left <= x < left+width and top <= y < top+height):
        return None
    return ((x-left)/width, (y-top)/height)


def drag_target(start, dx, dy, low, high):
    if not all(math.isfinite(v) for v in (start, dx, dy, low, high)) or low >= high:
        raise ValueError('Invalid joint drag')
    # Half a degree per logical pixel; independent of display DPI/resolution.
    return max(low, min(high, start + math.radians(.5)*(dx-dy)))


def joint_for_path(physics, path):
    from .robot import description, JOINT_NAMES
    matches = []
    for role, robot in physics.robots.items():
        for name in JOINT_NAMES:
            child = description(role)[2][name].find('child').get('link')
            link = physics.mapping.index_to_path[robot['bodies'][child]]
            if path == link or path.startswith(link+'/'):
                matches.append((len(link), role, name, link))
    if not matches:
        return None
    _, role, name, link = max(matches)
    return role, name, link
