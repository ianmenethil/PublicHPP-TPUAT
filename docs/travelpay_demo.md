# TravelPay Demo Extract

- Source: `https://payuat.travelpay.com.au/demo/`
- Extracted (UTC): `2025-12-29T02:51:00.260065Z`
- HTML SHA256: `60640158076c5152aaf82320ef9022fb3b112193b8e4c8cc3198f2f5ed6784f1`

## Code Sample

- Stylesheet: `https://cdn.<<PROGRAM DOMAIN>>.com.au/css/zenpay.payment.css` (https://cdn.b2bpay.com.au/css/zenpay.payment.css)
- Javascript: `https://cdn.<<PROGRAM DOMAIN>>.com.au/js/zenpay.payment.js` (https://cdn.b2bpay.com.au/js/zenpay.payment.js)

```js
var payment = $.zpPayment({
    url: 'https://<<PROGRAM SUB-DOMAIN>>.<<PROGRAM DOMAIN>>/online/v5',
    merchantCode: '<<MERCHANT-CODE>>',
    apiKey: '<<API-KEY>>',
    fingerprint: '<<FINGERPRINT>>',
    redirectUrl: '<<Your Redirect URL>>',
    mode: 0,
    displayMode: 0,
    customerName: 'Customer Name',
    customerReference: 'Reference 1',
    paymentAmount: 100.00,
    timeStamp: '<<TIMESTAMP>>'
});
var result = payment.init();
```

Notes:
- Include the following in your code
- The implementation depends on jQuery version 3.4.1 and requires jQuery to be included in your code.
- Execute the following jQuery code on the click of your ”Pay Now” button. PROGRAM DOMAIN , PROGRAM SUB-DOMAIN , and API-KEY will be provided by Zenith Payments. ( Note that these will be different for each environment i.e. Live and UAT ) For FINGERPRINT refer to the parameter details below.

## Input Parameters

- **url** (string, Required) — Plugin access url. We strongly recommend v5 integration.
- **merchantCode** (string, Required) — As provided by Zenith.
- **apiKey** (string, Required) — As provided by Zenith
- **fingerprint** (string, Required)
  - Fingerprint (v5) is a SHA3-512 hash of the following pipe-delimited string:
  - `apiKey|userName|password|mode|paymentAmount|merchantUniquePaymentId|timestamp`
  - Credentials provided by Zenith Payments are case sensitive.
  - Field notes:
  - `apiKey`: refer apiKey parameter
  - `userName`: provided by Zenith Payments
  - `password`: provided by Zenith Payments
  - `mode`: refer mode parameter
  - `paymentAmount`: amount in cents without symbol (e.g. $150.53 => 15053). Pass 0 when mode is 2.
  - `merchantUniquePaymentId`: refer merchantUniquePaymentId parameter
  - `timestamp`: current datetime in UTC ISO 8601 format (yyyy-MM-ddTHH:mm:ss).
- **redirectUrl** (string, Required) — The page will redirect to this URL with the result in the query string. Refer the return parameters section below.
- **redirectOnError** (string, Optional) — If this is set to true, all validation and processing errors are returned part of the redirect url. Default is 'false'.
- **mode** (int, Optional)
  - Must be one of the following three values
  - 0 - Make Payment
  - 1 - Tokenise
  - 2 - Custom Payment
  - 3 - Preauthorization
  - Defaults to 0 if not provided.
- **displayMode** (int, Optional)
  - Must be one of the following two values
  - 0 - Default (Modal)
  - 1 - Redirect Url
  - Defaults to 0 if not provided.
  - Google Pay and Apple Pay works if Modal or Redirect Url with iframe is used.
- **customerName** (string, Conditional) — Required if mode is set to 0 or 2.
- **CustomerNameLabel** (string, Optional) — Custom label to override default customer name display text
- **customerReference** (string, Conditional) — Required if mode is set to 0 or 2.
- **CustomerReferenceLabel** (string, Optional) — Custom label to override default customer reference display text
- **paymentAmount** (number, Conditional)
  - Required if mode is set to 0 or 2.
  - Returns applicable fee if provided with mode 1.
- **PaymentAmountLabel** (string, Optional) — Custom label to override default payment amount display text
- **allowBankAcOneOffPayment** (boolean (true/false), Conditional)
  - Required if mode is set to 0 or 2.
  - Show bank account option only if the option is enable for the merchant. Default is false.
- **allowPayToOneOffPayment** (boolean (true/false), Conditional)
  - Required if mode is set to 0 or 2.
  - Show PayTo bank account option only if the option is enable for the merchant. Default is false.
- **allowPayIdOneOffPayment** (boolean (true/false), Conditional)
  - Required if mode is set to 0 or 2.
  - Show PayID option only if the option is enable for the merchant. Default is false.
- **allowApplePayOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show Apple Pay option only if the option is enable for the merchant. Default is false.
- **allowGooglePayOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show Google Pay option only if the option is enable for the merchant. Default is false.
- **allowLatitudePayOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show Latitude Pay option only if the option is enable for the merchant. Default is false.
- **allowSlicePayOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show Slice Pay option only if the option is enable for the merchant. Default is false.
- **allowUnionPayOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show UnionPay option only if the option is enable for the merchant. Default is false.
- **allowAliPayPlusOneOffPayment** (boolean (true/false), Conditional)
  - Conditional if mode is set to 0.
  - Show AliPay+ option only if the option is enable for the merchant. Default is false.
- **showFeeOnTokenising** (boolean (true/false), Conditional)
  - Required if mode is set to 1.
  - Show the applicable fees for the token at the end of the process. Default is false.
- **showFailedPaymentFeeOnTokenising** (boolean (true/false), Conditional)
  - Optional if mode is set to 1.
  - Show the applicable failed payment fees for the token at the end of the process. Default is false.
- **merchantUniquePaymentId** (string, Required) — Payment id provided by the merchant. Must be unique and can not be reused if a transaction is processed using this id.
- **timestamp** (string, Conditional) — timestamp is required for v4 and optional for v3. Provide current datetime in UTC ISO 8601 format as timestamp. format: yyyy-MM-ddTHH:mm:ss
- **cardProxy** (string, Optional) — Use this parameter to make a payment using a card proxy which is generated using mode '1'.
- **callbackUrl** (string, Optional) — The URL will be called with HTTP POST method to submit the result. Refer the return parameters section below.
- **hideTermsAndConditions** (boolean (true/false), Optional)
  - This will hide the Terms and Conditions.
  - Defaults to 'false' if not provided.
- **sendConfirmationEmailToMerchant** (boolean (true/false), Optional)
  - This will send confirmation email to merchant.
  - Defaults to 'false' if not provided.
- **additionalReference** (string, Optional) — Additional reference to identify customer. This will be passed on to the merchant reconciliation file (PDF & CSV)
- **contactNumber** (string, Optional) — Contact number
- **customerEmail** (string, Conditional)
  - Email address to which invoice will be emailed if the merchant is configured.
  - It is mandatory in V4.
- **ABN** (string, Optional) — Australian Business Number. Used for reward programs if the Program is enabled to provide reward points.
- **companyName** (string, Optional) — Customer company name.
- **title** (string, Optional)
  - Plugin Title.
  - Defaults to 'Process Payment' if not provided.
- **hideHeader** (boolean (true/false), Optional)
  - This will hide the program header including program logo.
  - Defaults to 'true' if not provided.
- **hideMerchantLogo** (boolean (true/false), Optional)
  - This will hide the merchant logo if any.
  - Defaults to 'false' if not provided.
- **overrideFeePayer** (int, Optional)
  - Must be one of the following three values
  - 0 - Default (based on pricing profile)
  - 1 - Merchant (Merchant will pay the fee regardless of pricing profile setting)
  - 2 - Customer (Customer will pay the fee regardless of pricing profile setting)
  - Defaults to 0 if not provided.
- **departureDate** (string, Optional) — departureDate is required for Slice Pay. Provide date in UTC ISO 8601 format as departureDate. format: yyyy-MM-dd
- **userMode** (int, Optional)
  - Must be one of the following two values
  - 0 - Customer Facing - default (cardholder must enter CCV or 3DS)
  - 1 - Merchant Facing (for merchant use only - no CCV or 3DS) - if supported by merchant options.
- **minHeight** (int, Optional) — For Mode 0 and 2 height defaults to 725px, for mode 1 height defaults to 450px if not provided.
- **onPluginClose** (function, Optional) — Javascript callback function to execute when plug-in is closed.
- **sendConfirmationEmailToCustomer** (boolean (true/false), Optional)
  - This will send confirmation email to customer.
  - Defaults to 'false' if not provided.
- **allowSaveCardUserOption** (boolean (true/false), Optional)
  - This will allow to save the card information.
  - Defaults to 'false' if not provided.
  - This option will only work if 'Enable Plugin Pay & Save Card' option is enabled at program or merchant level.
- **sku1** (string, Optional) — Stock Keeping Unit – Optional text fields, allowing up to 50 alphanumeric characters. If the value exceeds 50 characters, only the first 50 characters will be retained and the rest discarded.
- **sku2** (string, Optional) — Stock Keeping Unit – Optional text fields, allowing up to 50 alphanumeric characters. If the value exceeds 50 characters, only the first 50 characters will be retained and the rest discarded.
## Return Parameters

### The following parameters are returned in mode 0 and 2. Same payload is also delivered in JSON format if callback URL is provided.

- **result**
  - Possible values (case insensitive):
  - success => Processing successful
  - failed => Processing failed
  - error => All validation errors and generic errors. This means, the plugin did not processed the request
- **CustomerName** — Same as input parameter.
- **CustomerReference** — Same as input parameter.
- **MerchantUniquePaymentId** — Same as input parameter.
- **AccountOrCardNo** — Account or card number used to process payment.
- **PaymentReference** — Payment reference. (applicable for Payment)
- **PreauthReference** — Preauthorization reference. (applicable for Preauthorization)
- **ProcessorReference** — Processor reference.
- **PaymentStatus**
  - Possiible values
  - 0 => (Pending)
  - 1 => (Error)
  - 3 => (Successful)
  - 4 => (Failed)
  - 5 => (Cancelled)
  - 6 => (Suppressed)
  - 7 => (InProgress)
- **PaymentStatusString**
  - Possiible values
  - Pending
  - Error
  - Successful
  - Failed
  - Cancelled
  - Suppressed
  - InProgress
- **PreauthStatus**
  - Possiible values
  - 0 => (Pending)
  - 1 => (Error)
  - 3 => (Successful)
  - 4 => (Failed)
  - 5 => (Cancelled)
  - 6 => (Suppressed)
  - 7 => (InProgress)
- **PreauthStatusString**
  - Possiible values
  - Pending
  - Error
  - Successful
  - Failed
  - Cancelled
  - Suppressed
  - InProgress
- **TransactionSource**
  - Possiible values
  - 36 => (Public_OnlineOneOffPayment)
- **TransactionSourceString**
  - Possiible values
  - Public_OnlineOneOffPayment
- **ProcessingDate**
  - The date and time when the payment is processed.
  - format:
  - yyyy-MM-ddTHH:mm:ss
- **SettlementDate**
  - The date when the payment is settled to the merchant.
  - format:
  - yyyy-MM-dd
- **IsPaymentSettledToMerchant** — Flag to indicate whetehr the funds are settled to the merchant or not.
- **BaseAmount** — Same as payment amount.
- **CustomerFee** — Fee charged to the the customer to process the payment.
- **ProcessedAmount** — Base amount + Customer fee. (applicable for Payment)
- **PreauthAmount** — Base amount + Customer fee. (applicable for Preauthorization)
- **FundsToMerchant** — Base amount - Merchant fee, if applicable.
- **MerchantCode** — Merchant code.
- **FailureCode** — Populated only when payment is not successful.
- **FailureReason** — Populated only when payment is not successful.
- **Token** — Returned only if payment is processed using cardProxy input parameter. The value will be same as cardProxy.
- **PayId** — Returned only if payment is processed using PayID.
- **PayIdName** — Returned only if payment is processed using PayID. Display name for the PayID

### The following parameters are returned in mode 1. Same payload is also delivered in JSON format if callback URL is provided.

- **Token** — The proxy that can be saved and then use to process payment using API or payment plugin.
- **CardType** — Type of card i.e. Visa, MasterCards, Ammercican Express Or Bank Account.
- **CardHolderName** — Card holder name provided by the user. Returned only if user selects credit / debit card.
- **CardNumber** — Obfuscated card number provided by the user. Returned only if user selects credit / debit card.
- **CardExpiry**
  - Card expiry date. Returned only if user selects credit / debit card.
  - format:
  - MM/CCYY
- **AccountName** — Account name provided by the user. Returned only if user selects bank account.
- **AccountNumber** — Obfuscated account number provided by the user. Returned only if user selects bank account.
- **PayId** — Returned only if payment is processed using PayID.
- **PayIdName** — Returned only if payment is processed using PayID. Display name for the PayID
- **IsRestrictedCard** — Flag to indicate whetehr the card is restricted or not.
- **PaymentAmount** — Same as input parameter.
- **CustomerFee** — Customer fee applicable to process a payment of amount specified in PaymentAmount input parameter.
- **MerchantFee** — Merchant fee applicable to process a payment of amount specified in PaymentAmount input parameter.
- **ProcessingAmount** — The total amount that will be processed i.e. PaymentAmount + CustomerFee.

## Error Codes

- **E01** — Make sure fingerprint and apikey are passed.
- **E02-\*** — MerchantUniquePaymentId cannot be empty.
- **E03-\***
  - The fingerprint should be unique everytime.
  - This can be achieved by using new MerchantUniquePaymentId and current Timestamp everytime the plugin is opened.
- **E04** — Invalid Credentials. Applicable for V1 and V2(V1 and V2 are deprecated).
- **E05** — Make sure fingerprint and apikey are passed.
- **E06** — Account is not active. Contact administrator.
- **E07** — Provided endpoint is not supported.
- **E08** — Invalid Credentials. Make sure fingerprint is correctly generated, refer to fingerprint generation logic.
- **E09** — Security violation. Close and open the plugin with fresh fingerprint.
- **E10** — Security violation. Close and open the plugin with fresh fingerprint.
- **E11** — Timestamp cannot be empty. Make sure to pass same timestamp as in generated fingerprint.
- **E13** — MerchantCode provided does not match with the provided credentials.
- **E14** — Security violation. Close and open the plugin with fresh fingerprint.
- **E15** — MerchantCode cannot be empty(V4 onwards).
- **E16** — Version can not be empty.
- **E17** — CustomerEmail can not be empty(V4 onwards).
- **E18** — DepartureDate is required for Slice Pay.
- **E19** — Invalid Timestamp. Timestamp needs to be in UTC ISO 8601 format.

