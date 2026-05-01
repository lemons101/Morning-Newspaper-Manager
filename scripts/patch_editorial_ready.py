from pathlib import Path
import json

p = Path('/root/projects/Morning-Newspaper-Manager/runtime/top10_editorial_ready.json')
data = json.loads(p.read_text(encoding='utf-8'))
patches = {
    'Show HN: Perfect Bluetooth MIDI for Windows': {
        'summary_main': '这是一款面向 Windows 的开源小工具，目标是把蓝牙 BLE MIDI 键盘稳定接入 Windows 的 MIDI 服务体系，让宿主软件、DAW 和 Web MIDI 应用像使用有线设备一样识别和使用无线键盘。作者围绕 Roland FP-90X 的实际排障过程，把配对成功但软件不可见、电脑回传音符无声，以及 MIDI 通道设置不一致等问题拆成了可定位、可修复的工程方案。',
        'why_it_matters': '这条值得看，不只是因为它发布了一个小工具，而是它把 Windows 蓝牙 MIDI 长期存在但体验很差的兼容问题，拆成了可复现、可解释、可修复的工程方案。对于做音乐软件、数字乐器连接或 Windows 音频工具链的人来说，这是一种很典型的“系统看似支持、实际并不好用”的缝隙修补案例。',
        'card_summary': '这是一款面向 Windows 的开源小工具，目标是把蓝牙 BLE MIDI 键盘稳定接入 Windows 的 MIDI 服务体系，让宿主软件、DAW 和 Web MIDI 应用像使用有线设备一样识别和使用无线键盘。作者围绕 Roland FP-90X 的实际排障过程，把配对成功但软件不可见、电脑回传音符无声，以及 MIDI 通道设置不一致等问题拆成了可定位、可修复的工程方案。'
    },
    "Running Adobe's 1991 PostScript Interpreter in the Browser": {
        'summary_main': '这篇文章把一段 1991 年随 HP LaserJet 扩展卡发布的 Adobe PostScript 解释器搬进了现代浏览器环境。作者通过模拟当年的 M68K 硬件和打印机外围接口，让原始 ROM 中的解释器在浏览器本地直接完成页面渲染，用户把 PostScript 文件拖进网页即可得到结果，全程不依赖服务器。',
        'why_it_matters': '这条值得看，因为它展示了一种很有代表性的“旧软件资产现代化”思路：不是重写一套兼容实现，而是把历史上的原始参考实现通过模拟层重新激活，并直接服务今天的使用场景。对于浏览器端计算、软件考古和数字保存领域的人来说，这不只是怀旧项目，而是一次把历史代码重新产品化的案例。',
        'card_summary': '这篇文章把一段 1991 年随 HP LaserJet 扩展卡发布的 Adobe PostScript 解释器搬进了现代浏览器环境。作者通过模拟当年的 M68K 硬件和打印机外围接口，让原始 ROM 中的解释器在浏览器本地直接完成页面渲染，用户把 PostScript 文件拖进网页即可得到结果，全程不依赖服务器。'
    },
    'Apple accidentally left Claude.md files Apple Support app': {
        'summary_main': '一则在社交平台传播的爆料称，Apple 在 Apple Support app 的一次更新中误带入了 Claude.md 文件，随后又通过紧急小版本将其移除。这类文件通常被视为 AI 编码工具的项目指令配置，因此事件被外界解读为 Apple 在部分开发流程中使用了 Claude 相关工具，也暴露出 AI 开发配置误入正式发行包的新型发布风险。',
        'why_it_matters': '这条值得看，不在于 Apple 是否使用 Claude 本身，而在于它暴露了一个新的软件供应链风险：除了密钥、证书和调试配置，面向 AI 编码工具的项目指令文件也可能被误打进正式发行包。随着 AI 开发助手深入主流软件工程流程，这类配置文件已经应该被纳入发布审查范围。',
        'card_summary': '一则在社交平台传播的爆料称，Apple 在 Apple Support app 的一次更新中误带入了 Claude.md 文件，随后又通过紧急小版本将其移除。这类文件通常被视为 AI 编码工具的项目指令配置，因此事件被外界解读为 Apple 在部分开发流程中使用了 Claude 相关工具，也暴露出 AI 开发配置误入正式发行包的新型发布风险。'
    },
    'Your Website Is Not for You': {
        'summary_main': '这篇文章讨论的不是具体网页技巧，而是一个常被管理层忽略的判断标准：网站首先是给用户完成任务用的，不是给老板、市场负责人或董事会表达个人审美的。作者指出，很多网站并不是缺少研究或专业能力，而是在评审过程中不断被非用户视角的主观偏好改写，最后做成了让内部满意、却未必真正好用的版本。',
        'why_it_matters': '这条值得看，因为它点出了产品设计和企业决策中一个非常普遍的问题：当决策者离品牌太近时，容易把网站当成自我表达，而不是转化工具。对于做产品、增长、设计管理或官网改版的人来说，这篇文章提醒大家把判断标准重新拉回用户任务、研究依据和实际效果。',
        'card_summary': '这篇文章讨论的不是具体网页技巧，而是一个常被管理层忽略的判断标准：网站首先是给用户完成任务用的，不是给老板、市场负责人或董事会表达个人审美的。作者指出，很多网站并不是缺少研究或专业能力，而是在评审过程中不断被非用户视角的主观偏好改写，最后做成了让内部满意、却未必真正好用的版本。'
    }
}
for item in data.get('items', []):
    t = item.get('title')
    if t in patches:
        item.update(patches[t])
        item['editorial_summary_hint'] = patches[t]['summary_main']
        item['summary_zh'] = patches[t]['summary_main']
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('patched editorial_ready')
