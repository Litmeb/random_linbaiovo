# Firebase Firestore 排行榜配置说明

本项目的排行榜使用 **Firebase Firestore** 存储分数。按以下步骤配置后，玩家即可上传自己的最高分并查看排行榜。

---

## 1. 创建 Firebase 项目

1. 打开 [Firebase 控制台](https://console.firebase.google.com/)
2. 点击「添加项目」或「创建项目」
3. 输入项目名称（如 `nanoi-leaderboard`），按提示完成创建（Analytics 可选关闭）

---

## 2. 启用 Firestore

1. 在项目概览左侧菜单点击 **「Firestore Database」**
2. 点击「创建数据库」
3. 选择 **「以测试模式启动」**（开发阶段；上线前请改为正式规则）
4. 选择离你较近的区域（如 `asia-east1`），确认创建

---

## 3. 设置 Firestore 安全规则

1. 在 Firestore 页面打开 **「规则」** 标签
2. 将规则替换为下面内容（允许所有人读/新增，不允许修改，允许凭 deleteToken 删除）：

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /leaderboard/{entry} {
      allow read: if true;
      allow create: if true;
      allow update: if false;
      allow delete: if true;
    }
    match /leaderboard_teaparty/{entry} {
      allow read: if true;
      allow create: if true;
      allow update: if false;
      allow delete: if true;
    }
  }
}
```
（删除由前端在验证 `deleteToken` 后执行；仅持有该条记录 token 的用户能通过界面发起删除。）

3. 点击「发布」

---

## 4. 获取 Web 应用配置

1. 在项目概览页点击 **齿轮图标 → 项目设置**
2. 在「您的应用」一栏点击 **「</>」**（Web 图标）添加应用
3. 填写应用昵称（如 `nanoi-game`），可不勾选 Firebase Hosting，点击「注册应用」
4. 复制出现的 `firebaseConfig` 对象（包含 `apiKey`、`authDomain`、`projectId` 等）

---

## 5. 填入 index.html

1. 打开项目中的 **`index.html`**
2. 搜索 **`firebaseConfig`**，找到类似下面的配置块：

```javascript
  const firebaseConfig = {
    apiKey: "AIzaSyDrbk_wOJfNohIVEFSgAAA9D2XUdMFK5i0",
    authDomain: "who-post-this.firebaseapp.com",
    projectId: "who-post-this",
    storageBucket: "who-post-this.firebasestorage.app",
    messagingSenderId: "549959020575",
    appId: "1:549959020575:web:9f78c757c79636d5b2252a",
    measurementId: "G-5L5DQG5680"
  };
```

3. 用你在第 4 步复制的真实配置，**完整替换**上述对象中的各字段（保留键名，只改值）
4. 保存文件

---

## 6. 验证

1. 用本地服务器打开页面（如 `python -m http.server 8080` 后访问）
2. 点击右上角 **「排行榜」**，应能打开弹窗（若未配置会显示「未配置 Firebase」）
3. 玩一局后点击 **「上传我的最高分」**，输入昵称，若配置正确会提示上传成功，排行榜列表会刷新

---

## 数据结构说明

- **集合名**：`leaderboard_teaparty`
- **每条记录字段**：
  - `nickname`（string）：玩家昵称，最多 20 字
  - `score`（number）：历史最高分
  - `correctRate`（number）：达成该最高分时的正确率（0–100）
  - `correctCount`（number）：达成该最高分时的正确题数
  - `createdAt`（timestamp）：上传时间，由 Firebase 自动写入
  - `deleteToken`（string）：删除用密钥，仅上传时由服务生成；排行榜列表接口不返回该字段，用于「仅本人可删」的校验

**排名规则**：先按总分从高到低，再按正确率从高到低，再按正答数从高到低。上传时若已存在「总分、正确率、正答数」完全相同的记录，会提示「已经存过」。

---

## 常见问题

- **打开排行榜显示「未配置 Firebase」**  
  检查 `index.html` 里的 `firebaseConfig` 是否已替换为真实配置，且 `projectId` 不是 `YOUR_PROJECT_ID`。

- **上传失败 / 控制台报权限错误**  
  确认 Firestore 规则已按第 3 步发布，且规则里包含 `leaderboard_teaparty` 的 `create: if true`。

- **想限制谁可以上传**  
  可后续改为使用 Firebase Auth 登录，在规则里写 `allow create: if request.auth != null` 等条件。
