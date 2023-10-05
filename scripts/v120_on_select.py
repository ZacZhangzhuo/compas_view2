from compas.geometry import Polygon, Polygon, Capsule
from compas_view2.app import App

viewer = App()

polygon = Polygon([[0, 0, 0], [1, 0, 0], [1, 1, 0]])
obj = viewer.add(polygon, linecolor=(0, 0, 1))

capsule = Capsule([[0, 0, 0], [0, 0, 1]], 0.3)
obj = viewer.add(capsule, facecolor=(0, 0, 1))


@viewer.on(interval=500)
def on_selected(frame):
    if len(viewer.selector.selected) == 1:
        print(f"You are selecting the {type(viewer.selector.selected[0]._data)} object.")


viewer.run()
