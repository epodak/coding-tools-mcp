import Cocoa
import Foundation

struct TipConfig: Codable {
    var title: String?
    var message: String?
    var action_url: String?
    var action_label: String?
    var duration: Double?
    var style: String?
    var sound: Bool?
}

final class FloatingHUD: NSObject, NSApplicationDelegate {
    private var panel: NSPanel?
    private var config: TipConfig = TipConfig()

    override init() {
        super.init()
        let args = CommandLine.arguments
        if args.count > 2 && args[1] == "--json-base64" {
            if let data = Data(base64Encoded: args[2]),
               let decoded = try? JSONDecoder().decode(TipConfig.self, from: data) {
                self.config = decoded
            }
        } else if args.count > 2 && args[1] == "--json-file" {
            if let data = try? Data(contentsOf: URL(fileURLWithPath: args[2])),
               let decoded = try? JSONDecoder().decode(TipConfig.self, from: data) {
                self.config = decoded
            }
        } else if args.count > 2 && args[1] == "--json" {
            let jsonString = args[2]
            if let data = jsonString.data(using: .utf8),
               let decoded = try? JSONDecoder().decode(TipConfig.self, from: data) {
                self.config = decoded
            }
        } else {
            self.config.title = args.count > 1 ? args[1] : "任务提示"
            self.config.message = args.count > 2 ? args[2] : "点击查看详情"
            self.config.action_url = args.count > 3 ? args[3] : nil
            self.config.duration = args.count > 4 ? Double(args[4]) : 45.0
            self.config.action_label = args.count > 5 ? args[5] : "查看网页版详情 ↗"
            self.config.style = args.count > 6 ? args[6] : "teal"
            self.config.sound = true
        }
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        let width: CGFloat = 416
        let height: CGFloat = 176

        guard let screen = NSScreen.main else {
            NSApp.terminate(nil)
            return
        }

        let visible = screen.visibleFrame
        let rect = NSRect(
            x: visible.maxX - width - 24,
            y: visible.maxY - height - 24,
            width: width,
            height: height
        )

        let p = NSPanel(
            contentRect: rect,
            styleMask: [.nonactivatingPanel, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        p.isFloatingPanel = true
        p.hidesOnDeactivate = false
        p.level = .floating
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        p.isMovableByWindowBackground = true
        p.backgroundColor = .clear
        p.isOpaque = false
        p.hasShadow = true
        p.animationBehavior = .utilityWindow

        // Background visual effect view (frosted glass)
        let bg = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: width, height: height))
        bg.material = .popover
        bg.blendingMode = .behindWindow
        bg.state = .active
        bg.wantsLayer = true
        bg.layer?.cornerRadius = 16
        bg.layer?.masksToBounds = true
        bg.layer?.borderWidth = 0.5
        bg.layer?.borderColor = NSColor.separatorColor.cgColor

        // Accent strip on left
        let accentColor: NSColor
        let styleName = (config.style ?? "teal").lowercased()
        switch styleName {
        case "green", "success":
            accentColor = NSColor(srgbRed: 0.10, green: 0.72, blue: 0.48, alpha: 1.0)
        case "orange", "warning":
            accentColor = NSColor.systemOrange
        case "blue":
            accentColor = NSColor(srgbRed: 0.02, green: 0.52, blue: 0.96, alpha: 1.0)
        case "purple":
            accentColor = NSColor.systemPurple
        default: // teal
            accentColor = NSColor(srgbRed: 0.08, green: 0.65, blue: 0.72, alpha: 1.0)
        }

        let accent = NSView(frame: NSRect(x: 0, y: 0, width: 6, height: height))
        accent.wantsLayer = true
        accent.layer?.backgroundColor = accentColor.cgColor
        bg.addSubview(accent)

        // Title
        let titleLabel = NSTextField(labelWithString: config.title ?? "任务提示")
        titleLabel.font = NSFont.systemFont(ofSize: 15, weight: .bold)
        titleLabel.textColor = NSColor.labelColor
        titleLabel.frame = NSRect(x: 24, y: 132, width: 366, height: 24)
        bg.addSubview(titleLabel)

        // Message
        let msgLabel = NSTextField(wrappingLabelWithString: config.message ?? "")
        msgLabel.font = NSFont.systemFont(ofSize: 12.5, weight: .regular)
        msgLabel.textColor = NSColor.secondaryLabelColor
        msgLabel.maximumNumberOfLines = 4
        msgLabel.frame = NSRect(x: 24, y: 56, width: 368, height: 70)
        bg.addSubview(msgLabel)

        // Action button & Close button
        let hasAction = config.action_url != nil && !(config.action_url!.isEmpty)
        if hasAction {
            let actionBtn = NSButton(title: config.action_label ?? "查看网页版详情 ↗", target: self, action: #selector(openAction(_:)))
            actionBtn.bezelStyle = .rounded
            actionBtn.frame = NSRect(x: 20, y: 14, width: 184, height: 32)
            actionBtn.keyEquivalent = "\r"
            bg.addSubview(actionBtn)

            let closeBtn = NSButton(title: "关闭", target: self, action: #selector(closeTip(_:)))
            closeBtn.bezelStyle = .rounded
            closeBtn.frame = NSRect(x: 304, y: 14, width: 88, height: 32)
            bg.addSubview(closeBtn)
        } else {
            let okBtn = NSButton(title: "知道了", target: self, action: #selector(closeTip(_:)))
            okBtn.bezelStyle = .rounded
            okBtn.frame = NSRect(x: 294, y: 14, width: 98, height: 32)
            okBtn.keyEquivalent = "\r"
            bg.addSubview(okBtn)
        }

        p.contentView = bg
        p.orderFrontRegardless()
        panel = p

        // Optional sound
        if config.sound ?? true {
            NSSound(named: "Glass")?.play()
        }

        // Auto expire timer with smooth fade out
        let duration = max(5.0, config.duration ?? 45.0)
        Timer.scheduledTimer(withTimeInterval: duration, repeats: false) { [weak self] _ in
            self?.fadeOutAndTerminate()
        }
    }

    private func fadeOutAndTerminate() {
        guard let p = self.panel else {
            NSApp.terminate(nil)
            return
        }
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.35
            p.animator().alphaValue = 0.0
        }, completionHandler: {
            NSApp.terminate(nil)
        })
    }

    @objc private func openAction(_ sender: Any?) {
        if let raw = config.action_url, let url = URL(string: raw) {
            NSWorkspace.shared.open(url)
        }
        fadeOutAndTerminate()
    }

    @objc private func closeTip(_ sender: Any?) {
        fadeOutAndTerminate()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

let app = NSApplication.shared
let delegate = FloatingHUD()
app.delegate = delegate
app.run()
