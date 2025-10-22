
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
    print(url)
    #url = url.replace("0.0.0.0","3.23.18.185")
#     url = url.replace(
#     f"http://{base_client.client_host}:{base_client.client_port}",
#     f"https://wanglab.tech/tiles/{token}"
# )
    url = url.replace(
    f"http://{base_client.client_host}:{base_client.client_port}",
    f"http://localhost:{base_client.client_port}"
    )
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

        layer_url = layer_url.replace(
         f"http://{base_client.client_host}:{base_client.client_port}",
          f"http://localhost:{base_client.client_port}"
         )
    
        layer = dl.BaseLayer(
            dl.TileLayer(
                opacity=1,
                url=layer_url,
                maxZoom=max_zoom,
                minZoom=default_zoom,
            ),
            name=arg_name,checked=checked
        )

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
        colorbar1 = dl.Colorbar(colorscale=['#219cd1'], width=20, height=20, min=0, max=1, position="bottomleft", nTicks=3, tickText=['', 'aneuploid', ''],style={"color":"#1EC01E"})
        colorbar2 = dl.Colorbar(colorscale=['#1bb547'], width=20, height=20, min=0, max=1, position="bottomleft", nTicks=3, tickText=['', 'diploid', ''],style={"color":"#1EC01E"})
        colorbar3 = dl.Colorbar(colorscale=['#be6ca7'], width=20, height=20, min=0, max=1, position="bottomleft", nTicks=3, tickText=['', 'None', ''],style={"color":"#1EC01E"})

    # create map
    # PZhang added this (deal with empty input regions)
    # 2/25/2025
    if geojson_coords is None:
        geojson_coords = []

    thor_map = dl.Map(
        id=map_id,
        children=[
           
            colorbar3,
            colorbar2,
            colorbar1,
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
