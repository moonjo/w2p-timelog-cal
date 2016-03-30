(function ($, window, document) {
    'use strict';
    
    var Timeduration = function(element, options) {
        this.widget = '';
        this.$element = $(element);
        this.defaultTime = options.defaultTime;
        this.disableFocus = options.disableFocus;
        this.disableMousewheel = options.disableMousewheel;
        this.minuteStep = options.minuteStep;
        this.snapToStep = options.snapToStep;
        this.template = options.template;
        this.maxHours = options.maxHours;
        this._init();
    };
    
    Timeduration.prototype = {
        constructor: Timeduration,
        _init: function() {
            var self = this;
            if (this.template) {
                this.$element.on({
                    'focus.timeduration':$.proxy(this.showWidget, this),
                    'click.timeduration':$.proxy(this.showWidget, this),
                    'blur.timeduration':$.proxy(this.blurElement, this),
                    'mousewheel.timeduration DOMMouseScroll.timeduration': $.proxy(this.mousewheel, this)
                });
            } else {
                this.$element.on({
                    'focus.timeduration':$.proxy(this.highlightUnit, this),
                    'click.timeduration':$.proxy(this.highlightUnit, this),
                    'keydown.timeduration':$.proxy(this.elementKeydown, this),
                    'blur.timeduration':$.proxy(this.blurElement, this),
                    'mousewheel.timeduration DOMMouseScroll.timeduration': $.proxy(this.mousewheel, this)
                });
            }
            
        },
        blurElement: function() {
            this.highlightedUnit = null;
            this.updateFromElementVal();
        },
        clear: function() {
            this.hour = 0;
            this.minute = 0;
            this.$element.val('00:00');
        }
        decrementHout: function() {
            if (this.hour <= 0) {
                this.hour = this.maxHours - 1;
            } else {
                this.hour--;
            }
        },
        decrementMinute: function() {
            var newval;
            if (step) {
                newval = this.minute - step;
            } else {
                newval = this.minute - this.minuteStep;
            }
            
            if (newval < 0) {
                this.decrementHour();
                this.minute = newval + 60;
            } else {
                this.minute = newval;
            }
        },
        elementKeydown: function(e) {
            switch (e.which) {
                case 9: //tab
                    if (e.shiftKey) {
                        if (this.highlighedUnit == 'hour') {
                            break;
                        }
                        this.highlightPrevUnit();
                    } else if ( ( this.highlightedUnit ==='minute')) {
                        break;
                    } else {
                        this.highlightNextUnit();
                    }
                    e.preventDefault();
                    this.updateFromElementVal();
                    break;
                case 27: //escape
                    this.updateFromElementVal();
                    break;
                case 37: // left arrow
                    e.preventDefault();
                    this.highlightPrevUnit();
                    this.updateFromElementVal();
                    break;
                case 38: // up arrow
                    e.preventDefault();
                    switch (this.highlightedUnit) {
                        case 'hour':
                            this.incrementHour();
                            this.highlightHour();
                            break;
                        case 'minute':
                            this.incrementMinute();
                            this.highlightMinute();
                            break;
                    }
                    this.update();
                    break;
                case 39: // right arrow
                    e.preventDefault();
                    this.highlightNextUnit();
                    this.updateFromElementVal();
                    break;
                case 40:
                    e.preventDefault();
                    switch (this.highlightedUnit) {
                        case 'hour':
                            this.decrementHour();
                            this.highlightHour();
                            break;
                        case 'minute':
                            this.decrementMinute();
                            this.highlightMinute();
                            break;
                    }
                    this.update();
                    break;
            }
        }
    },
    getTemplate: function() {
        var template,
            hourTemplate,
            minuteTemplate,
            templateContent;
        
    },
    
    
    $.fn.timeinput = function(){
        return $(this).each(function(){ 
            
            var input = $(this);
            
            // get the associated label using the input's id
            var label = $('label[for="'+input.attr('id')+'"]');
            
            // wrap the input + label in a div 
            input.add(label).wrapAll('<div class="custom-'+ input.attr('type') +'"></div>');
            
            // necessary for browsers that don't support the :hover pseudo class on labels
            label.hover(
                function(){ $(this).addClass('hover'); },
                function(){ $(this).removeClass('hover'); }
            );
            
            //bind custom event, trigger it, bind click,focus,blur events                   
            input.bind('updateState', function(){   
                input.is(':checked') ? label.addClass('checked') : label.removeClass('checked checkedHover checkedFocus'); 
            })
            .trigger('updateState')
            .click(function(){ 
                $('input[name="'+ $(this).attr('name') +'"]').trigger('updateState'); 
            })
            .focus(function(){ 
                label.addClass('focus'); 
                if(input.is(':checked')){  $(this).addClass('checkedFocus'); } 
            })
            .blur(function(){ label.removeClass('focus checkedFocus'); });
            
        });
    };

}(jQuery));