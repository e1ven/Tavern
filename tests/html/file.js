(function(){
	var _waitUntilExists = {
		pending_functions : [],
		loop_and_call : function()
		{
			if(!_waitUntilExists.pending_functions.length){return}
			for(var i=0;i<_waitUntilExists.pending_functions.length;i++)
			{	
				var obj = _waitUntilExists.pending_functions[i];
				var resolution = document.getElementById(obj.id);
				if(obj.id == document){
					resolution = document.body;
				}
				if(resolution){
					var _f = obj.f;
					_waitUntilExists.pending_functions.splice(i, 1)
					if(obj.c == "itself"){obj.c = resolution}
					_f.call(obj.c)							
					i--					
				}
			}
		},
		global_interval : setInterval(function(){_waitUntilExists.loop_and_call()},5)
	}
	if(document.addEventListener){
		document.addEventListener("DOMNodeInserted", _waitUntilExists.loop_and_call, false);
		clearInterval(_waitUntilExists.global_interval);
	}
	window.waitUntilExists = function(id,the_function,context){
		context = context || window
		if(typeof id == "function"){context = the_function;the_function = id;id=document}
		_waitUntilExists.pending_functions.push({f:the_function,id:id,c:context})
	}
	waitUntilExists.stop = function(id,f){
		for(var i=0;i<_waitUntilExists.pending_functions.length;i++){
			if(_waitUntilExists.pending_functions[i].id==id && (typeof f == "undefined" || _waitUntilExists.pending_functions[i].f == f))
			{
				_waitUntilExists.pending_functions.splice(i, 1)
			}
		}
	}
	waitUntilExists.stopAll = function(){
		_waitUntilExists.pending_functions = []
	}
})();


function include_dom(script_filename) {
    var html_doc = document.getElementsByTagName('head').item(0);
    var js = document.createElement('script');
    js.setAttribute('language', 'javascript');
    js.setAttribute('type', 'text/javascript');
    js.setAttribute('src', script_filename);
    html_doc.appendChild(js);
    return false;
}
        
        

waitUntilExists("PageContainer",function(){
    
initial_page_text = "<div id=\"limits\">	<header id=\"top\">		<a href=\"http://www.pluric.com/\"><img src=\"/images/logo.png\" alt=\"Pluric\" /></a>	</header>			<div id=\"content\">				<div id=\"container3\">		<div id=\"container2\">		<div id=\"container1\">			<div id=\"left\">				<h2>Categories</h2>					<ul>						<li><a href=\"#\">#Egypt</a></li>						<li><a href=\"#\">#Python</a></li>						<li><a href=\"#\">#StarTrek</a></li>						<li><a href=\"#\">#Apple</a></li>						<li><a href=\"#\">#Linux</a></li>					</ul>								<h2>Interesting People</h2>					<ul>						<li><a href=\"#\">#Egypt</a></li>						<li><a href=\"#\">#Python</a></li>						<li class=\"active\"><a href=\"#\">#StarTrek</a></li>						<li><a href=\"#\">#Apple</a></li>						<li><a href=\"#\">#Linux</a></li>					</ul>											</div><!-- #left -->						<div id=\"center\">				<h2>Topics by @user</h2>					<ul>						<li><a href=\"#\">Topic Title Here</a></li>						<li class=\"active\"><a href=\"#\">Another Topic Title Here</a></li>						<li><a href=\"#\">Yet Anotner Topic Title Here</a></li>						<li><a href=\"#\">Nope, not this one</a></li>						<li><a href=\"#\">I lied, That One too</a></li>					</ul>										</div><!-- #center -->						<div id=\"right\">				<div class=\"thread\">					<h2>Thread Discussion</h2>					<div class=\"padder\">											<div class=\"topic_title\">							<h3>Another Topic Title Here</h3>							<p class=\"meta\">4:59pm Today</p>						</div><!-- .topic_title -->												<div class=\"thread_right\">							<img class=\"avatar\" src=\"/images/avatar.jpg\" />							<a class=\"username\" href=\"#\">@matt</a><br />							<a href=\"#\">follow</a>						</div><!-- .thread_right -->												<div class=\"clear\"></div>												<div class=\"thread_start\">							<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga.</p>							<p>Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus.</p>						</div><!-- .thread_start -->										</div><!-- .padder -->											<ul class=\"response\">								<li>									<div class=\"comment_avatar\">										<img class=\"avatar\" src=\"/images/avatar.jpg\" />									</div><!-- .comment_avatar -->																		<div class=\"comment_body\">										<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. </p>										<p class=\"response_meta\">5:01pm Today by @johnJones <a href=\"#\"><img class=\"imginline\" src=\"/images/t_up.png\" alt=\"good comment\" /></a> <a href=\"#\"><img class=\"imginline\" src=\"/images/t_down.png\" alt=\"bad comment\" /></a> </p>									</div>								</li>									<ul>										<li>											<div class=\"comment_avatar\">												<img class=\"avatar\" src=\"/images/avatar.jpg\" />											</div><!-- .comment_avatar -->																						<div class=\"comment_body\">												<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. </p>												<p class=\"response_meta\">5:01pm Today by @johnJones <a href=\"#\"><img class=\"imginline\" src=\"/images/t_up.png\" alt=\"good comment\" /></a> <a href=\"#\"><img class=\"imginline\" src=\"/images/t_down.png\" alt=\"bad comment\" /></a> </p>											</div>																							<ul>													<li>														<div class=\"comment_avatar\">															<img class=\"avatar\" src=\"/images/avatar.jpg\" />														</div><!-- .comment_avatar -->																												<div class=\"comment_body\">															<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. </p>															<p class=\"response_meta\">5:01pm Today by @johnJones <a href=\"#\"><img class=\"imginline\" src=\"/images/t_up.png\" alt=\"good comment\" /></a> <a href=\"#\"><img class=\"imginline\" src=\"/images/t_down.png\" alt=\"bad comment\" /></a> </p>														</div>													</li>												</ul>																					</li>									</ul>																	<li>									<div class=\"comment_avatar\">										<img class=\"avatar\" src=\"/images/avatar.jpg\" />									</div><!-- .comment_avatar -->																		<div class=\"comment_body\">										<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. </p>										<p class=\"response_meta\">5:01pm Today by @johnJones <a href=\"#\"><img class=\"imginline\" src=\"/images/t_up.png\" alt=\"good comment\" /></a> <a href=\"#\"><img class=\"imginline\" src=\"/images/t_down.png\" alt=\"bad comment\" /></a> </p>									</div>								</li>																<li>									<div class=\"comment_avatar\">										<img class=\"avatar\" src=\"/images/avatar.jpg\" />									</div><!-- .comment_avatar -->																		<div class=\"comment_body\">										<p>At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. </p>										<p class=\"response_meta\">5:01pm Today by @johnJones <a href=\"#\"><img class=\"imginline\" src=\"/images/t_up.png\" alt=\"good comment\" /></a> <a href=\"#\"><img class=\"imginline\" src=\"/images/t_down.png\" alt=\"bad comment\" /></a> </p>									</div>								</li>						</ul><!-- .response -->										</div><!-- .thread -->							</div><!-- #right -->		</div><!-- #container1 -->		</div><!-- #container2 -->		</div><!-- #container3 -->				<div class=\"clear\"></div>		</div><!-- #content -->		<footer id=\"footer\">	</footer></div><!-- #limits -->";


document.getElementById("PageContainer").innerHTML=initial_page_text;    
    
})



/* Remote Script call inspired by http://www.phpied.com/javascript-include/ */

/*
 * Wait Until Exists Version v0.2 - http://javascriptisawesome.blogspot.com/
 *
 *
 * TERMS OF USE - Wait Until Exists
 * 
 * Open source under the BSD License. 
 * 
 * Copyright © 2011 Ivan Castellanos
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without modification, 
 * are permitted provided that the following conditions are met:
 * 
 * Redistributions of source code must retain the above copyright notice, this list of 
 * conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice, this list 
 * of conditions and the following disclaimer in the documentation and/or other materials 
 * provided with the distribution.
 * 
 * Neither the name of the author nor the names of contributors may be used to endorse 
 * or promote products derived from this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 *  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
 *  GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED 
 * AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 *  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED 
 * OF THE POSSIBILITY OF SUCH DAMAGE. 
 *
*/
