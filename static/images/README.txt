Put real photos here to replace the CSS placeholder colors used on the
homepage carousel (see templates/home.html):

  farmer_field.jpg        - a farmer standing in a field
  mandi_produce.jpg       - crates of produce at a mandi
  transport_truck.jpg     - a loaded truck on a rural road
  storage_warehouse.jpg   - a grain storage warehouse
  village_aerial.jpg      - an aerial view of a village / farmland

Then in static/css/style.css, replace each .slide-field / .slide-mandi /
.slide-transport / .slide-storage / .slide-village gradient with:

  background: url('../images/YOUR_FILE.jpg') center/cover no-repeat;

Keep the file names, or update templates/home.html and style.css to match
whatever names you use.
