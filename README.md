# hass-onvif

### 功能说明

这是两个插件：

1. 针对 home assistant v0.115.2的略微修改过的onvif集成（支持最近两三年的新版本onvif摄像头），通过该组件，配合Hass APP，可以实现摄像头播放界面上按住云台的上下左右不动，摄像头将持续旋转知道松开按住的按钮为止（home assistant自带的onvif组件是每次指定云台转动时间，无法根据界面操作动态决定）；
2. 针对比较老的onvif摄像头（比如三四年前的，至于有啥区别没去研究过，反正一些老的摄像头无法用hass自带的集成接入进来，试试这个组件即可），由于hass自带的onvif库的版本和这种老版本的插件所需要的onvif库名字相同（都是onvif-py3）但是版本不兼容，所以就做到同室相处就比较麻烦，解决方案是直接把老版本用的库名字改成了onvif)13放置到home assistant的依赖目录中了。

### 安装部署

1. 如果只需要第一个功能，则拷贝custom_components/onvif到home assistant的配置目录下的custom_components中即可；
2. 如果要使用第二个功能，则拷贝custom_components/onvif2到home assistant的配置目录下的custom_components中，并且合并deps到home assistant配置目录下的deps中（注意备份）

### 使用配置

1. 如果使用第一个功能，拷贝之后，使用home assistant中的系统集成添加onvif，然后按照向导输入摄像头IP和端口，用户密码即可使用；
2. 如果使用第二个功能，则需要手动修改配置文件configuration.yaml：

``` yaml
camera:
  - platform: onvif2
    host: 192.168.2.242
    port: 8899
```

其中：

* host：onvif摄像头的IP地址
* port：onvif摄像头的onvif端口，注意不是http端口（比如TPLINK的可能是2020，水星的可能就是80），可以使用ONVIF工具进行搜索查找端口

### 关于APP

如果你使用HASS APP，需要在个性化配置文件customize.yaml中为摄像头配置类型、预览地址以及TTS的input_text组件（可选），比如：

``` yaml
camera.onvif_camera:
  preview_url: rtsp://user:pwd@yourdomain:port/stream=0.sdp?real_stream
  tts_sensor: input_text.broadcast
  friendly_name: 摄像头
  type: hass_old
```

其中：

* preview_url：可以在外网播放的RTSP地址，也可以使用onvif工具进行查找
* tts_sensor：在APP上如果发现有这个配置，就会显示一个输入框，供你在播放摄像头的时候向家里发送TTS消息
* type：摄像头类型，以便APP知道怎么发送onvif控制指令，三种类型：
  * hass_old：使用onvif2插件的老版本onvif摄像头
  * hass：使用了上述onvif插件的新版本摄像头，可以直接持续转动
  * 空（不设置type）：就是home assistant自带的onvif协议，APP端的处理方式是在按下按钮期间每隔500ms发送一次转动指令

Enjoy it!