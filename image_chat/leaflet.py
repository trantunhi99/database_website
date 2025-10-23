
from niceview.utils.tools import CMAX, CMIN, get_hex_values
import dash_leaflet as dl

def create_leaflet_map(
    map_id,
    base_client,
    base_layer,
    list_of_layers,
    cmax=CMAX,
    classes=None,
    cmap=None,
    geojson_coords=None,
    token="",
):
    """Create leaflet map.
    
    Args:
        map_id (str): Map ID.
        base_client (TileClient): Base client.
        base_layer (TileLayer): Base layer.
        list_of_layers (list[tuple]): List of layers.
        cmax (int, optional): Max value.
        cmap: (str, optional): Color map.
        geojson_coords: input coordinate 
        token: user token
        
    Returns:
        Map
    """

     # viewport
    default_center = [base_client.center()[0], base_client.center()[1]]
    max_zoom = base_client.max_zoom
    
    # viewport bounds
    expanded_bounds = list(base_layer.bounds)
    expanded_bounds[0] = list(expanded_bounds[0])
    expanded_bounds[1] = list(expanded_bounds[1])
    vert_dst = (expanded_bounds[1][1] - expanded_bounds[0][1]) 
    hori_dst = (expanded_bounds[1][0] - expanded_bounds[0][0])
    expanded_bounds[0][1] -= vert_dst
    expanded_bounds[1][0] += vert_dst
    expanded_bounds[0][0] -= hori_dst
    expanded_bounds[1][1] += hori_dst
    # zoom factor
    zoom_factor = 1 * ((vert_dst + hori_dst) / 2) / 0.0085
    default_zoom = base_client.default_zoom + zoom_factor
    
    # overlay

    overlay_layers = []
    url = base_layer.url
    print("initial url:", url)
    #url = url.replace("0.0.0.0","3.23.18.185")
#     url = url.replace(
#     f"http://{base_client.client_host}:{base_client.client_port}",
#     f"https://wanglab.tech/tiles/{token}"
# )
    url = url.replace(
    f"http://{base_client.client_host}:{base_client.client_port}",
    f"http://localhost:{base_client.client_port}"
    )

    print("after url:", url)
    base_input = dl.BaseLayer(
        dl.TileLayer(
                url=url,
                maxZoom=max_zoom,
                minZoom=default_zoom,
            ),name="base layer", checked="base layer"
        )
    overlay_layers.append(base_input)
    for index, (arg_layer, arg_name) in enumerate(list_of_layers):
        checked = index == len(list_of_layers) - 1
        layer_url = arg_layer.url
        #layer_url = layer_url.replace("0.0.0.0","3.23.18.185")
#         layer_url = layer_url.replace(
#     f"http://{base_client.client_host}:{base_client.client_port}",
#     f"https://wanglab.tech/tiles/{token}"
# )
        print("initial layer url:", layer_url)
        layer_url = layer_url.replace(
         f"http://{base_client.client_host}:{base_client.client_port}",
          f"http://localhost:{base_client.client_port}"
         )

        print("after layer url:", layer_url)

        layer = dl.BaseLayer(
            dl.TileLayer(
                opacity=1,
                url=layer_url,
                maxZoom=max_zoom,
                minZoom=default_zoom,
            ),
            name=arg_name,checked=checked
        )
        
        # checked = index == len(list_of_layers) - 1 
        # layer = dl.Overlay(
        #     dl.TileLayer(
        #         opacity=1,
        #         url=layer_url,
        #         maxZoom=max_zoom,
        #         minZoom=default_zoom,
        #     ),
        #     name=arg_name,
        #     checked=checked
        # )

        overlay_layers.append(layer)
    
    width, height = 20, 200
    if classes is None:
        if cmap is not None:
            colorbar1 = dl.Colorbar(
                    colorscale=get_hex_values(cmap), width=width, height=height, position='bottomleft',nTicks=2, tickText=['MIN', 'MAX'], style={"color":"#1EC01E"}
                    )
            colorbar2 = []
            colorbar3 = []
        else:
            colorbar1 = []
            colorbar2 = []
            colorbar3 = []
    else:
        COLOR_DICT_CELLS = {
            0: [92, 20, 186],      # Deep purple — Neoplastic
            1: [255, 0, 0],        # Bright red — Immune
            2: [34, 221, 77],      # Bright green — Stromal
            3: [35, 92, 236],      # Strong blue — Epithelial
            4: [255, 209, 102],    # Soft yellow-orange — Fibroblast
            5: [255, 159, 68],     # Warm orange — Endothelial
            6: [200, 50, 50],      # Medium red — Cardiomyocyte (distinct from Immune)
            7: [60, 40, 120],      # Deep indigo — Cardiac Fibroblast
            8: [35, 192, 236],     # Sky blue — Smooth Muscle
            9: [254, 255, 100],    # Pale yellow — Adipose
            10: [153, 102, 255],   # Lavender — Oligodendrocyte
            11: [255, 159, 168],   # Light pink — Astrocyte
            12: [255, 59, 68],     # Bright coral red — Neuron
            13: [92, 200, 186],    # Teal — Vascular Smooth Muscle
            14: [255, 0, 100],     # Magenta — Alveolar pneumocytes
            15: [34, 221, 177],    # Aqua green — Chondrocytes
            16: [35, 92, 136],     # Steel blue — Hepatocyte
            17: [254, 55, 0],      # Vivid orange-red — Glia
            18: [120, 68, 229],    # Violet — Pericentral hepatocytes
            19: [68, 133, 229],    # Azure — Proliferating keratinocytes
            20: [120, 229, 68],    # Lime green — Spinous keratinocytes
            21: [0, 180, 229],     # Aqua-blue — Connective
            22: [120, 0, 68],      # Maroon — Lamina propria
            23: [229, 180, 68],    # Golden tan — Reserved / extra
            24: [229, 68, 180],    # Hot pink — Reserved / extra
            25: [68, 229, 120],    # Mint green — Reserved / extra
        }


    TYPE_NUCLEI_DICT_PANNUKE = {
        1: "Neoplastic", 2: "Immune", 3: "Stromal", 4: "Epithelial", 5: "Fibroblast",
        6: "Endothelial", 7: "Cardiomyocyte", 8: "Cardiac Fibroblast", 9: "Smooth Muscle",
        10: "Adipose", 11: "Oligodendrocyte", 12: "Astrocyte", 13: "Neuron",
        14: "Vascular Smooth Muscle", 15: "Alveolar pneumocytes", 16: "Chondrocytes",
        17: "Hepatocyte", 18: "Glia", 19: "Pericentral hepatocytes",
        20: "Proliferating keratinocytes", 21: "Spinous keratinocytes",
        22: "Connective", 23: "Lamina propria",
    }

    # Generate colorbars only for present classes
    colorbars = []
    offset = 0  # vertical stacking offset
    for idx in classes:
        if idx in TYPE_NUCLEI_DICT_PANNUKE and idx in COLOR_DICT_CELLS:
            name = TYPE_NUCLEI_DICT_PANNUKE[idx]
            # print(name)
            rgb = COLOR_DICT_CELLS[idx]
            hex_color = '#%02x%02x%02x' % tuple(rgb)  # dynamic hex color

            # EXACT same format as your example + proper stacking offset
            cb = dl.Colorbar(
                colorscale=[hex_color],
                width=20,
                height=20,
                min=0,
                max=1,
                position="bottomleft",
                nTicks=3,
                tickText=['', name, ''],
                style={
                    # readable modern text
                    "color": "#1e1e1e",  # neutral dark gray for contrast
                    "fontFamily": "SF Pro Text, -apple-system, BlinkMacSystemFont, sans-serif",
                    "fontWeight": "500",
                    "fontSize": "13px",
                    "letterSpacing": "-0.25px",

                    # clean container look
                    "backgroundColor": "rgba(255, 255, 255, 0.9)",
                    "borderRadius": "6px",
                    "padding": "4px 10px",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",

                    # alignment tweaks
                    "margin": "0px",
                    "transform": f"translateY(-{offset}px)",
                }
            )



            colorbars.append(cb)
            offset += 0  # pixel spacing between colorbars

    # create map
    # PZhang added this (deal with empty input regions)
    # 2/25/2025
    if geojson_coords is None:
        geojson_coords = []

    thor_map = dl.Map(
        id=map_id,
        children=[
            *reversed(colorbars),
            dl.LayersControl(
                overlay_layers, hideSingleBase=True, id="layer-overlay"
            ),
            #dl.EasyButton(icon="fa-home", id="btn_home"),
            dl.FullScreenControl(),
            dl.FeatureGroup(
                [
                    # PZhang put all the polygons inside the FeatureGroup so they can be seen by EditControl (editable)
                    # There is still a bug with revisualize button (deleting all the polygons does not clear the file)
                    # 2/25/2025
                    *[dl.Polygon(positions=coords) for coords in geojson_coords],
                    dl.EditControl(
                        id='editControl',
                        draw={
                            'polyline': False,
                            'polygon': True,
                            'rectangle': True,
                            'circle': False,
                            'circlemarker': False,
                            'marker': False,
                        },
                    ),
                ],
            ),
            dl.EasyButton(icon="fa-save", id="btn_save"),
            # Alex add this to plot the polygons on the map, 
            # 2/25/2025
            #dl.Polygon(positions=geojson_coords),
            #dl.EasyButton(icon="fa-search",id="btn_find",title="Choose area"),
            # dl.ScaleControl(imperial=False),
        ],
        center=default_center,
        zoom=default_zoom,
        style={"width":"100%",'height': '700px', 'margin': 'auto', 'display': 'block', 'background': 'white'},
        attributionControl=False,
        trackViewport=True,
        maxBounds=expanded_bounds,
    )
    return thor_map
