var express = require('express');
 var app = express();

app.get('/api/v1/status', function (req, res) {
 res.end( JSON.stringify({status:"ok",version:1}) );
 })

var server = app.listen(8765, function () {
 console.log("Example app listening at http://%s:%s", server.address().address, server.address().port)

})
