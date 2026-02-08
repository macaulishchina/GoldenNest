# 资产登记系统重构方案

## 一、需求分析

### 当前问题
1. **概念混淆**：
   - "资金注入"(Deposit) 和 "理财配置"(Investment) 分离
   - 用户需要在两个入口操作，体验不统一
   
2. **业务逻辑**：
   - Deposit：记录现金存入，增加余额，计入股权
   - Investment：配置理财产品（定期、基金、股票等），从余额扣款
   
3. **用户期望**：
   - 统一的"资产登记"入口
   - 支持多种资产类型：活期、定期、基金、股票等

## 二、重构方案

### 2.1 核心设计思路

**取消"余额"概念，一切都是资产**

- **旧设计**：Deposit 增加余额 → Investment 从余额扣款 → 维护 balance_after
- **新设计**：所有资金都是 Asset，通过 `deduct_from_cash` 控制资金流转
  - Activity 现金也是一种资产类型（CASH）
  - 其他资产可选择是否从活期扣除
  - Transaction 记录活期资产变化，而非"总余额"

**关键改进**：
1. ✅ 更符合真实场景：可以直接买股票，不必先存入活期
2. ✅ 灵活性：用户自主决定资金来源
3. ✅ 简化逻辑：不需要维护"虚拟余额"概念

### 2.2 数据模型变更

#### 枚举类型调整

```python
# 原 InvestmentType 改为 AssetType
class AssetType(str, enum.Enum):
    """资产类型"""
    CASH = "cash"                    # 活期现金（原deposit功能）
    TIME_DEPOSIT = "time_deposit"    # 定期存款
    FUND = "fund"                    # 基金
    STOCK = "stock"                  # 股票
    BOND = "bond"                    # 债券
    OTHER = "other"                  # 其他

# 🌟 NEW: 货币类型
class CurrencyType(str, enum.Enum):
    """货币类型"""
    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    HKD = "HKD"  # 港元
    JPY = "JPY"  # 日元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    AUD = "AUD"  # 澳元
    CAD = "CAD"  # 加元
    SGD = "SGD"  # 新加坡元
    KRW = "KRW"  # 韩元
```

#### Investment 表重命名为 Asset

```python
class Asset(Base):
    """资产登记表（原Investment）"""
    __tablename__ = "assets"  # 重命名表
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 🌟 资产归属人（用于股权计算）
    name: Mapped[str] = mapped_column(String(100))  # 资产名称
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType))  # 资产类型
    
    # 💰 多币种支持
    currency: Mapped[CurrencyType] = mapped_column(SQLEnum(CurrencyType), default=CurrencyType.CNY)  # 🌟 货币类型
    foreign_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 外币金额
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 汇率（外币→CNY）
    principal: Mapped[float] = mapped_column(Float)  # 本金（CNY，用于股权计算）
    
    expected_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 预期年化收益率
    start_date: Mapped[datetime] = mapped_column(DateTime)  # 开始日期
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 到期日期（活期为空）
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 银行/机构名称
    deduct_from_cash: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否从活期扣除
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creat
1. 取消"余额"概念，只有各类资产
2. 增加 `deduct_from_cash` 控制资金来源
3. 增加 `user_id` 明确股权归属
4. 支持多币种，汇率自动计算

| 资产类型 | 是否从活期扣除 | 到期日期 | 货币支持 | 生成Deposit记录 |
|---------|---------------|---------|---------|---------------|
| CASH（活期） | ❌ 否（外部注入） | ❌ 无 | 仅 CNY | ✅ 是（归属 user_id） |
| TIME_DEPOSIT | ✅ **可选** | ✅ 可选 | 多币种 | ✅ 是（归属 user_id） |
| FUND/STOCK   | ✅ **可选** | ❌ 无 | 多币种 | ✅ 是（归属 user_id） |
| BOND/OTHER   | ✅ **可选** | ✅ 可选 | 多币种 | ✅ 是（归属 user_id） |

**使用场景示例**：

**场景 1: 人民币活期存入**
```python
用户 A 发工资存入 5000 CNY
→ Asset(
    user_id=A, 
    type=CASH, 
    currency=CNY,
    principal=5000,
    deduct_from_cash=False
)
→ Deposit(user_id=A, amount=5000)  # 股权归 A
```

**场景 2: 从活期购买人民币基金**
```python
用户 B 从活期转 3000 CNY 买基金
→ Asset(
    user_id=B,
    type=FUND,
    currency=CNY,
    principal=3000,
    deduct_from_cash=True
)
→ 活期 -3000, 无新 Deposit（股权不变）
```

**场景 3: 直接购买美元基金**
```python
用户 A 购买 $500 美元基金（汇率 7.20）
→ Asset(
    user_id=A,
    type=FUND,
    currency=USD,
    foreign_amount=500,
    exchange_rate=7.20,
    principal=3600,  # 500 * 7.20
    deduct_from_cash=False
)
→ Deposit(user_id=A, amount=3600)  # 股权归 A，按 CNY 计算
→ Transaction(amount=3600, description="购买美元基金 $500 @7.20")
```

**场景 4: 增持美元基金**
```python
用户 A 已有 $500 @7.20（平均汇率 7.20）
再购买 $300 @7.30
→ 计算新的平均汇率:
   weighted_rate = (500*7.20 + 300*7.30) / (500+300)
                 = (3600 + 2190) / 800
                 = 7.2375
→ 更新 Asset:
   foreign_amount = 800
   exchange_rate = 7.2375
   principal = 5800
→ Deposit(user_id=A, amount=2190)  # 新增股权按新买入的 CNY 计算
```是（记录本金） |
| BOND/OTHER   | ✅ **可选** | ✅ 可选 | ✅ 可以 | ✅ 是（记录本金） |

**使用场景示例**：
1. 发工资存入 5000 → 登记 CASH 资产（不扣活期）
2. 从活期转 3000 买基金 → 登记 FUND 资产（勾选"从活期扣除"）
3. 直接买入股票 2000 → 登记 STOCK 资产（不扣活期，外部资金直接买入）

### 2.3 Transaction 表调整

**旧逻辑**：
```python
# balance_after 表示"总余额"
transaction.balance_after = previous_balance + amount  # Deposit
transaction.balance_after = previous_balance - amount  # Investment
```

**新逻辑**：
```python
# balance_after 改为表示"活期资产余额"
# 只有涉及活期的操作才更新 Transaction

if asset_type == CASH or deduct_from_cash:
    transaction = Transaction(
        transaction_type=...,
        amount=...,
        balance_after=current_cash_balance ± amount,  # 只反映活期变化
        reference_type="asset",
        reference_id=asset.id
    )
```

**Dashboard 展示逻辑**：
```python
# 旧：显示"总余额"（容易误导）
total_balance = latest_transaction.balance_after

# 新：分类展示
cash_balance = sum(Asset.principal where asset_type=CASH and is_active=True)
investment_total = sum(Asset.principal where asset_type!=CASH and is_active=True)
total_assets = cash_balance + investment_total
```

### 2.4 API 变更

#### 路由整合

```
原有：
- POST /api/deposit/create          → 资金注入
- POST /api/investment/create       → 理财配置

新方案：
- POST /api/asset/create            → 统一资产登记
- GET  /api/asset/list              → 资产列表（支持类型筛选）
- GET  /api/asset/summary           → 资产汇总
- POST /api/asset/{id}/income       → 登记收益
- PUT  /api/asset/{id}              → 编辑资产
- DELETE /api/asset/{id}            → 删除资产
```

#### 审批流程调整

**核心变化**：
```python
def execute_asset_create(asset_data):
    """执行资产登记"""
    user_id = asset_data["user_id"]  # 🌟 资产归属人
    currency = asset_data["currency"]  # 🌟 货币类型
    
    # 1. 计算 CNY 本金（用于股权）
    if currency == CurrencyType.CNY:
        principal_cny = asset_data["principal"]
        foreign_amount = None
        exchange_rate = None
    else:
        # 外币：获取实时汇率
        exchange_rate = get_realtime_exchange_rate(currency)
        foreign_amount = asset_data["foreign_amount"]
        principal_cny = foreign_amount * exchange_rate
    
    # 2. 创建资产记录
    asset = Asset(
        user_id=user_id,  # 🌟 明确归属
        currency=currency,
        foreign_amount=foreign_amount,
        exchange_rate=exchange_rate,
        principal=principal_cny,  # CNY 金额
        **other_fields
    )
    
    # 3. 计算活期余额变化
    if asset.asset_type == AssetType.CASH:
        # 活期注入：增加活期余额
        cash_change = +principal_cny
        create_deposit = True  # 外部注资，计入股权
    elif asset.deduct_from_cash:
        # 从活期转入其他资产：减少活期余额
        current_cash = get_cash_balance()
        if current_cash < principal_cny:
            raise InsufficientBalanceError()
        cash_change = -principal_cny
        create_deposit = False  # 内部转换，不计入股权
    else:
        # 外部资金直接买入：不影响活期
        cash_change = 0
        create_deposit = True  # 外部注资，计入股权
    
    # 4. 更新 Transaction（仅在有活期变化时）
    if cash_change != 0:
        create_transaction(cash_change, currency, exchange_rate)
    
    # 5. 创建 Deposit 记录（用于股权计算）
    if create_deposit:
        create_deposit_record(
            user_id=user_id,  # 🌟 股权归属
            amount=principal_cny  # 按 CNY 计算股权
        )

def execute_asset_increase(asset_id, increase_data):
    """执行资产增持（处理汇率平均）"""
    asset = get_asset(asset_id)
    user_id = increase_data["user_id"]  # 🌟 操作人
    
    if asset.currency == CurrencyType.CNY:
        # 人民币：直接增加
        new_principal_cny = increase_data["amount"]
        new_foreign_amount = None
        new_exchange_rate = None
    else:
        # 外币：计算加权平均汇率
        new_foreign_amount = increase_data["foreign_amount"]
        current_exchange_rate = get_realtime_exchange_rate(asset.currency)
        new_principal_cny = new_foreign_amount * current_exchange_rate
        
        # 🌟 计算新的平均汇率
        total_foreign = asset.foreign_amount + new_foreign_amount
        total_cny = asset.principal + new_principal_cny
        new_exchange_rate = total_cny / total_foreign
        
        # 更新资产的汇率记录
        asset.foreign_amount = total_foreign
        asset.exchange_rate = new_exchange_rate
    
    # 更新本金
    asset.principal += new_principal_cny
    
    # 创建持仓记录
    create_position(
        asset_id=asset_id,
        operation_type=INCREASE,
        foreign_amount=new_foreign_amount,
        exchange_rate=current_exchange_rate,  # 本次操作汇率
        amount=new_principal_cny
    )
    
    # 处理活期/股权逻辑（同 create）
    ...

def execute_asset_income(asset_id, income_data):
    """执行收益登记（外币收益按汇率转换）"""
    asset = get_asset(asset_id)
    
    if asset.currency == CurrencyType.CNY:
        income_cny = income_data["amount"]
        foreign_income = None
        exchange_rate = None
    else:
        # 外币收益：更新外币价值，收益按汇率转 CNY 计入活期
        new_foreign_value = income_data["current_foreign_value"]
        current_exchange_rate = get_realtime_exchange_rate(asset.currency)
        
        # 计算外币收益
        foreign_income = new_foreign_value - asset.foreign_amount
        income_cny = foreign_income * current_exchange_rate
        
        # 更新资产外币金额（不更新本金，收益计入活期）
        asset.foreign_amount = new_foreign_value
        exchange_rate = current_exchange_rate
    
    # 创建收益记录
    create_income(
        asset_id=asset_id,
        foreign_amount=foreign_income,
        exchange_rate=exchange_rate,
        amount=income_cny  # CNY 收益计入活期
    )
    
    # 收益增加活期余额
    create_transaction(+income_cny, description=f"收益: {asset.name}")
```

**关键逻辑说明**：

1. **user_id 归属**：
   - 所有 Asset 都必须指定 user_id
   - Deposit 记录也关联 user_id
   - 股权计算基于 user_id 聚合 Deposit

2. **汇率计算**：
   - 初次购买：记录实时汇率
   - 增持：计算加权平均汇率 = 总CNY / 总外币
   - 收益：按实时汇率转换 CNY

3. **股权计算**：
   - 始终以 CNY 计算股权
   - 外币资产换算为 CNY 后计入 Deposit
   - 汇率变动不影响已记录的股权（除非卖出）

## 五、影响范围评估

### 5.1 无需修改（✅ 兼容）

| 模块 | 依赖关系 | 是否受影响 | 说明 |
|-----|---------|-----------|-----|
| **成就系统** | 依赖 Deposit 表统计 | ✅ 无影响 | Deposit 表保留，统计逻辑不变 |
| **宠物系统** | 监听 deposit 事件 | ✅ 无影响 | 仍然创建 Deposit 记录，事件正常触发 |
| **股权计算** | 基于 Deposit 表（CNY） | ✅ 无影响 | Deposit 表保留，外币换算为 CNY 后记录 |
| **交易流水** | 记录 Transaction | ✅ 轻微调整 | 外币交易记录时附加汇率信息 |

### 5.2 需要修改（⚠️ 调整）

| 模块 | 修改内容 | 优先级 | 复杂度 |
|-----|---------|-------|-------|
| **后端模型** | Investment → Asset 重命名，增加多币种字段 | P0 | ⭐⭐⭐ |
| **后端API** | deposit + investment → asset 统一，增加汇率服务 | P0 | ⭐⭐⭐⭐ |
| **审批流程** | 合并审批类型，增加汇率计算和加权平均逻辑 | P0 | ⭐⭐⭐⭐⭐ |
| **前端路由** | 更新菜单项和路由配置 | P1 | ⭐ |
| **前端界面** | Deposit + Investment → Asset 统一，增加币种选择 | P1 | ⭐⭐⭐⭐ |
| **数据库迁移** | 重命名表和字段，增加外币相关字段 | P0 | ⭐⭐⭐ |
| **汇率服务** | 创建外汇汇率获取和缓存服务 | P0 | ⭐⭐⭐ |

### 5.3 成就系统详细影响

**无需修改的触发器**：
- ✅ `deposit_count` - 基于 Deposit 表
- ✅ `total_deposit` - 基于 Deposit 表
- ✅ `single_deposit` - 基于 context 参数
- ✅ `deposit_days` - 基于 Deposit 表

**需要调整的触发器**：
- ⚠️ `investment_count` - Investment → Asset（表名变更）
- ⚠️ `investment_type_count` - InvestmentType → AssetType（类型变更）
- ⚠️ `income_count` - InvestmentIncome → AssetIncome（表名变更）

## 四、实施步骤

### Phase 1: 后端数据模型 (P0)

1. 创建数据库迁移脚本
   - [ ] 重命名 `investments` → `assets`
   - [ ] 重命名 `investment_type` → `asset_type`
   - [ ] 添加 `user_id` 字段到 Asset 表
   - [ ] **添加 `currency` 字段到 Asset 表**
   - [ ] **添加 `foreign_amount` 字段到 Asset 表**
   - [ ] **添加 `exchange_rate` 字段到 Asset 表**
   - [ ] **添加 `deduct_from_cash` 字段到 Asset 表**
   - [ ] 添加 `bank_name` 字段到 Asset 表
   - [ ] 添加 CASH 类型到 AssetType 枚举
   - [ ] **创建 CurrencyType 枚举**
   - [ ] 重命名相关表（investment_incomes → asset_incomes, investment_positions → asset_positions）
   - [ ] **更新 AssetPosition 表：添加 foreign_amount, exchange_rate 字段**
   - [ ] **更新 AssetIncome 表：添加 foreign_amount, exchange_rate 字段**

2. 更新模型定义
   - [ ] `models.py`: Investment → Asset
   - [ ] `models.py`: InvestmentIncome → AssetIncome
   - [ ] `models.py`: InvestmentPosition → AssetPosition
   - [ ] `models.py`: InvestmentType → AssetType
   - [ ] **`models.py`: 添加 CurrencyType 枚举**
   - [ ] **`models.py`: 更新 Transaction 的注释说明（balance_after 表示活期余额）**

3. 创建辅助服务
   - [ ] **创建 `services/exchange_rate.py`**：
     - `get_realtime_exchange_rate(currency)` - 获取实时汇率
     - `calculate_weighted_exchange_rate(old_amount, old_rate, new_amount, new_rate)` - 计算加权平均汇率
   - [ ] 创建 `get_cash_balance(family_id)` 函数（计算活期资产总额）
   - [ ] 创建 `check_cash_sufficient(family_id, amount)` 函数（检查活期是否充足）

### Phase 2: 后端 API (P0)

1. 创建新的 asset.py 路由
   - [ ] POST /api/asset/create - 统一资产登记
     - **支持 currency, foreign_amount, exchange_rate 参数**
     - **支持 user_id 指定归属人**
     - 支持 deduct_from_cash 参数
   - [ ] GET /api/asset/list - 资产列表（支持类型筛选）
     - **按币种分组显示**
     - **显示外币金额和汇率**
   - [ ] GET /api/asset/summary - 资产汇总
     - **分类统计：活期 CNY、定期 CNY、外币（按币种）**
     - **计算总资产（CNY）**
   - [ ] GET /api/asset/cash-balance - 获取当前活期余额
   - [ ] **GET /api/asset/exchange-rate/{currency}** - 获取实时汇率

2. 更新审批流程 (approval.py)
   - [ ] 合并 deposit 和 investment_create 为 asset_create
   - [ ] 实现 `_execute_asset_create()` 方法：
     - **处理多币种：获取实时汇率，计算 CNY 本金**
     - **明确 user_id 归属**
     - 根据 asset_type 和 deduct_from_cash 决定活期变化
     - 检查活期余额充足性（如果 deduct_from_cash=True）
     - 决定是否创建 Deposit 记录（不从活期扣除时创建）
     - 只在活期变化时创建 Transaction
   - [ ] 实现 `_execute_asset_increase()` 方法：
     - **外币增持：计算加权平均汇率**
     - ****资产归属选择**（默认当前用户，可选其他家庭成员）
   - [ ] 资产类型选择（活期/定期/基金/股票/债券/其他）
   - [ ] **币种选择**（CNY/USD/HKD/JPY/EUR/GBP 等）
   - [ ] **汇率自动获取**：选择外币后自动显示实时汇率
   - [ ] **资金来源选择**：
     - 外部注入（新增资金，计入股权）
     - 从活期转入（设置 deduct_from_cash=true，不计入股权）
   - [ ] 动态表单字段：
     - **人民币资产**：金额、日期、归属人
     - **外币资产**：外币金额、币种、汇率（自动获取）、等额 CNY（自动计算）
     - 定期：+ 银行、利率、到期日、资金来源
     - 基金/股票：+ 名称、机构、资金来源
   - [ ] **活期余额提示**（当选择"从活期转入"时，显示当前可用余额）
   - [ ] **余额不足警告**（实时校验）
   - [ ] **外币增持提示**：显示当前平均汇率 vs 实时汇率

2. 更新路由和菜单
   - [ ] Layout.vue: "资金注入" + "理财" → "资产登记"
   - [ ] router/index.ts: /deposit + /investment → /asset

3. 更新 Dashboard.vue
   - [ ] **分币种展示资产**：
     - 活期余额卡片（CNY only）
     - 人民币投资卡片（定期/基金/股票）
     - 外币投资卡片（按币种分组）
       - 显示外币金额
       - 显示平均汇率
       - 显示等额 CNY
     - 总资产汇总（CNY）
   - [ ] **饼图**：资产分布（按类型 + 币种）
   - [ ] **折线图**：资产增长趋势（CNY）
   - [ ] **汇率变动提示**：外币资产价值波动

4. 更新 Approval.vue
   - [ ] 处理新的 asset_create 审批类型
   - [ ] **显示资产归属人**
   - [ ] **显示币种和汇率信息**
   - [ ] 显示资金来源信息

5. 更新资产详情和编辑
   - [ ] **显示外币金额、汇率、CNY 价值**
   - [ ] **增持时显示汇率计算逻辑**
   - [ ] **收益登记支持外币价值更新**额、机构、资金来源
   - [ ] 活期余额提示（当选择"从活期转入"时，显示当前可用余额）
   - [ ] 余额不足警告（实时校验）

2. 更新路由和菜单
   - [ ] Layout.vue: "资金注入" + "理财" → "资产登记"
   - [ ] router/index.ts: /deposit + /investment → /asset

3. 更新 Dashboard.vue
   - [ ] **分类展示资产**：
     - 活期余额卡片
     - 定期投资卡片
     - 基金卡片
     - 股票卡片
     - 总资产汇总
   - [ ] 饼图：资产分布
   - [ ] 折线图：资产增长趋势

4. 更新 Approval.vue
   - [ ] 处理新的 asset_create 审批类型
   - [ ] 显示资金来源信息

### Phase 4: 成就系统更新 (P2)

1. 更新触发器查询
   - [ ] investment_count: Investment → Asset
   - [ ] investment_type_count: InvestmentType → AssetType
   - [ ] income_count: InvestmentIncome → AssetIncome

2. 新增成就类型（可选）
   - [ ] 活期存款相关成就
   - [ ] 资产多样化成就

### Phase 5: 测试验证 (P3)

1. 单元测试
   - [ ] Asset CRUD 操作
   - [ ] 审批流程测试（CASH vs 其他类型）
   - [ ] 余额变化逻辑测试

2. 集成测试
   - [ ] 完整资产登记流程
   - [ ] 成就解锁测试
   - [ ] 宠物经验测试

3. 数据迁移验证
   - [ ] 旧数据正常显示
   - [ ] 股权计算准确

## 五、风险评估

| 风险项 | 影响 | 缓解措施 |
|-------|-----|---------|
| 数据库迁移失败 | 高 | 1. 完整备份<br>2. 分步迁移<br>3. 回滚方案 |
| 活期余额计算错误 | 高 | 1. 单元测试覆盖<br>2. 迁移后数据校验<br>3. 前端实时显示余额 |
| 股权计算错误 | 高 | 保留 Deposit 表不变，新逻辑向 Deposit 写入 |
| 成就统计错误 | 中 | 全量测试所有成就触发器 |
| 用户体验混乱 | 中 | 1. 清晰的 UI 提示<br>2. 资金来源选择明确<br>3. 余额实时显示 |
| Transaction 表语义变化 | 中 | 1. 更新注释说明<br>2. 前端不直接依赖 balance_after |

## 六、关键设计决策说明

### 6.1 为什么保留 Deposit 表？

**原因**：
1. 股权计算依赖 Deposit 表的存款记录和日期
2. 成就系统依赖 Deposit 表统计
3. 宠物系统监听 Deposit 事件

**策略**：
- Deposit 表作为"股权贡献记录表"
- 只有外部注资才创建 Deposit 记录（deduct_from_cash=False）
- 资产间转换不计入股权（deduct_from_cash=True）

### 6.2 Transaction 表的 balance_after 含义变化

**旧含义**：总余额（活期 + 投资 - 支出）
**新含义**：活期资产余额

**为什么改**：
- 旧设计中"总余额"包含已投资的钱，容易误导
- 新设计中只跟踪活期变化，更清晰
- Dashboard 通过汇总 Asset 表计算总资产，更准确

### 6.3 deduct_from_cash 的业务逻辑

| deduct_from_cash | 场景 | 活期余额 | Deposit 记录 | 股权计算 |
|-----------------|-----|---------|-------------|---------|
| False | 外部注资 | 增加（CASH）或不变 | ✅ 创建 | ✅ 计入 |
| True | 资产转换 | 减少 | ❌ 不创建 | ❌ 不计入 |

**示例**：
```
用户 A:
1. 发工资 5000 → Asset(CASH, 5000, deduct_from_cash=False)
   → 活期 +5000, Deposit +5000, 股权 +5000
   
2. 转 3000 买基金 → Asset(FUND, 3000, deduct_from_cash=True)
   → 活期 -3000, 无 Deposit, 股权不变
   
3. 直接买股票 2000 → Asset(STOCK, 2000, deduct_from_cash=False)
   → 活期不变, Deposit +2000, 股权 +2000
```

**结果**：
- 活期余额：2000
- 基金：3000
- 股票：2000
- 总资产：7000
- 股权贡献：7000（5000工资 + 2000股票）

## 六、回滚方案

如果重构失败，可以：
1. 保留原 deposit 和 investment 路由（标记为 deprecated）
2. Asset 表可以与 Investment 表并存
3. 前端保留 Deposit.vue 和 Investment.vue

## 八、时间估算

- Phase 1 (后端模型): **8-10 小时**（增加多币种字段和汇率服务）
- Phase 2 (后端 API): **10-14 小时**（复杂的汇率计算和加权平均逻辑）
- Phase 3 (前端界面): **14-18 小时**（币种选择、汇率显示、归属人选择）
- Phase 4 (成就系统): 2-3 小时
- Phase 5 (测试验证): **8-10 小时**（重点测试汇率计算和加权平均）

**总计**: **42-55 小时**

## 九、优化建议

1. **渐进式重构**：
   - Step 1: 先实现 Asset 系统（仅 CNY），保留原 deposit/investment API
   - Step 2: 前端迁移到新 Asset.vue
   - Step 3: 验证无误后添加多币种支持
   - Step 4: 废弃旧 API

2. **数据校验工具**：
   ```python
   # 迁移后校验脚本
   def validate_cash_balance():
       """校验活期余额计算正确性"""
       calculated = sum(Asset.principal where type=CASH and is_active)
       from_transaction = Transaction.last().balance_after
       assert calculated == from_transaction
   
   def validate_deposit_records():
       """校验 Deposit 记录完整性"""
       # 所有 deduct_from_cash=False 的资产应有对应 Deposit
       ...
   
   def validate_exchange_rates():
       """校验外币资产汇率正确性"""
       for asset in Asset where currency != CNY:
           assert asset.principal == asset.foreign_amount * asset.exchange_rate
   ```

3. **用户体验优化**：
   - 首次登记资产时显示引导提示
   - 清晰说明"外部注入"和"从活期转入"的区别
   - 实时显示活期可用余额
   - **外币选择时实时显示汇率和等额 CNY**
   - **增持外币时提示汇率变化**

4. **性能优化**：
   - 缓存活期余额计算结果
   - 缓存外汇汇率（1 小时）
   - Dashboard 使用汇总接口，避免前端多次请求
   - 使用 Redis 缓存汇率数据（生产环境）

## 十、FAQ

**Q1: 为什么不直接删除 Deposit 表？**
A: Deposit 表用于股权计算和成就统计，删除会导致历史数据丢失和逻辑复杂化。保留作为内部记录，外部只感知 Asset。Deposit 记录的是 CNY 金额，外币资产换算后记录。

**Q2: Transaction 表的 balance_after 还有用吗？**
A: 有用，但含义变为"活期余额（CNY）"而非"总余额"。前端不应直接依赖，应通过 /api/asset/cash-balance 获取。

**Q3: 旧数据如何迁移？**
A: 
- 旧 Deposit → Asset(type=CASH, currency=CNY, deduct_from_cash=False)
- 旧 Investment → Asset(type=原类型, currency=CNY, deduct_from_cash=True)
- 所有旧数据默认 CNY，exchange_rate=1.0

**Q4: 如何防止活期余额为负？**
A: 在 _execute_asset_create 中，如果 deduct_from_cash=True，先检查活期余额是否充足，不足则抛出异常，利用 savepoint 回滚。

**Q5: 支出申请时余额检查逻辑？**
A: 支出只能从活期扣款，检查活期余额（sum Asset where type=CASH）是否充足。

**Q6: 外汇汇率如何获取？**
A: 
- 方案 1（推荐）：使用免费 API（exchangerate-api.com 或 frankfurter.app），缓存 1 小时
- 方案 2：管理员手动配置汇率（Family 表存储）

**Q7: 增持外币资产时，汇率如何计算？**
A: 使用加权平均：
```
新汇率 = (旧外币金额 × 旧汇率 + 新买入外币金额 × 新买入汇率) / (旧外币金额 + 新买入外币金额)
```
例如：已有 $500 @7.20，再买 $300 @7.30
```
新汇率 = (500×7.20 + 300×7.30) / 800 = 7.2375
```

**Q8: 外币资产的股权如何计算？**
A: 始终以 CNY 计算股权。外币资产首次购买时，按当时汇率换算为 CNY 记录到 Deposit 表。后续汇率变动不影响已记录的股权，除非卖出或赎回。

**Q9: 外币收益如何处理？**
A: 
- 更新资产的 foreign_amount（外币总价值）
- 计算外币收益 = 新价值 - 旧价值
- 按实时汇率转换为 CNY 
- CNY 收益计入活期余额

**Q10: 为什么要指定 user_id（资产归属人）？**
A: 
- 明确每笔资产由谁贡献，方便股权计算
- Deposit 记录关联 user_id，股权按用户聚合
- 支持夫妻分别管理各自的外币账户
- 更符合真实家庭财务管理场景

**Q11: 如果汇率 API 不可用怎么办？**
A: 
- 使用备用 API（配置多个汇率源）
- 降级到上次缓存的汇率
- 允许用户手动输入汇率
- 管理员配置的兜底汇率
