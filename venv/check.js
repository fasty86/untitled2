"use strict"
 let input = document.querySelector('input');
            input.onkeyup = function() {
                let uname = $("#uname").val()
                condole.log(uname)
                $.get('/check?q=' + $("#uname").val(), function(data) {
                    alert(data);
                });
            };