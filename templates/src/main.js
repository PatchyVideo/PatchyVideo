
/*import Vue from '../node_modules/vue/dist/vue.js'*/
/*import login from './login.vue'*/
/*var login={
    template:"  <h1>这是登录组件，使用 .vue 文件定义出来的 </h1>"
}*/
import $ from 'jquery'
$(function () {
    $('li:odd').css('backgroundColor','blue');
})
/*var vm = new Vue({
  el: '#app',
  data: {
    msg: '123'
  }/!*,components:{
   login
    },*!/
  // components: {
  //   login
  // }
  /!* render: function (createElements) { // 在 webpack 中，如果想要通过 vue， 把一个组件放到页面中去展示，vm 实例中的 render 函数可以实现
    return createElements(login)
  } *!/
 /!*   render:function(createElements){
        //createElements是一个方法，调用它，它能够把指定的组建模板，渲染为html结构
        return createElements(login);
        //注意：，这里return的结果，会替换页面中el指定的那个容器
    }*!/

})*/


// 总结梳理： webpack 中如何使用 vue :
// 1. 安装vue的包：  cnpm i vue -S
// 2. 由于 在 webpack 中，推荐使用 .vue 这个组件模板文件定义组件，所以，需要安装 能解析这种文件的 loader    cnpm i vue-loader vue-template-complier -D
// 3. 在 main.js 中，导入 vue 模块  import Vue from 'vue'
// 4. 定义一个 .vue 结尾的组件，其中，组件有三部分组成： template script style
// 5. 使用 import login from './login.vue' 导入这个组件
// 6. 创建 vm 的实例 var vm = new Vue({ el: '#app', render: c => c(login) })
// 7. 在页面中创建一个 id 为 app 的 div 元素，作为我们 vm 实例要控制的区域；
