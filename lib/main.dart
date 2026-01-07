import 'package:flutter/material.dart';
import 'services/api_service.dart';

void main() {
  runApp(const SmartQueueApp());
}

class SmartQueueApp extends StatelessWidget {
  const SmartQueueApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Smart Queue',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.teal),
      home: const QueueScreen(),
    );
  }
}

class QueueScreen extends StatefulWidget {
  const QueueScreen({super.key});

  @override
  State<QueueScreen> createState() => _QueueScreenState();
}

class _QueueScreenState extends State<QueueScreen> {
  final api = ApiService();

  Map<String, dynamic>? queueData;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    loadQueue();
  }

  Future<void> loadQueue() async {
    try {
      setState(() => isLoading = true);

      queueData = await api.getQueue();
    } catch (e) {
      print("ERROR 🔴 $e");
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Failed to load queue: $e")));
    } finally {
      setState(() => isLoading = false);
    }
  }

  // -------------------------
  // API ACTIONS
  // -------------------------

  Future<void> addCustomer(String name, String phone) async {
    await api.addCustomer(name, phone);
    await loadQueue();
  }

  Future<void> finishCustomer(int id) async {
    await api.finish(id);
    await loadQueue();
  }

  Future<void> markArrived(int id) async {
    await api.arrived(id);
    await loadQueue();
  }

  Future<void> markNoShow(int id) async {
    await api.noShow(id);
    await loadQueue();
  }

  // -------------------------
  // ADD CUSTOMER DIALOG
  // -------------------------

  void showAddDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Add Customer"),
        content: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: nameController,
                decoration: const InputDecoration(labelText: "Name"),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? "Name required" : null,
              ),
              TextFormField(
                controller: phoneController,
                decoration: const InputDecoration(labelText: "Phone"),
                keyboardType: TextInputType.phone,
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return "Phone required";
                  if (v.trim().length != 10) return "Enter 10-digit number";
                  if (!RegExp(r'^[0-9]+$').hasMatch(v)) return "Digits only";
                  return null;
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () async {
              if (formKey.currentState!.validate()) {
                await addCustomer(
                  nameController.text.trim(),
                  phoneController.text.trim(),
                );
                Navigator.pop(context);
              }
            },
            child: const Text("Add"),
          ),
        ],
      ),
    );
  }

  // -------------------------
  // UI
  // -------------------------

  @override
  Widget build(BuildContext context) {
    final seated = queueData?["seated"] ?? [];
    final waiting = queueData?["waiting"] ?? [];

    return Scaffold(
      appBar: AppBar(title: const Text("Smart Queue - Barber")),
      floatingActionButton: FloatingActionButton(
        onPressed: showAddDialog,
        child: const Icon(Icons.person_add),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: loadQueue,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                children: [
                  // --------------- seated ---------------
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        "In Shop",
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Chip(
                        label: Text("${seated.length} / 3"),
                        backgroundColor: Colors.teal.shade50,
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  ...seated.map<Widget>((c) {
                    return Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 3,
                      margin: const EdgeInsets.symmetric(vertical: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            CircleAvatar(
                              radius: 26,
                              child: Text(
                                (c["name"] as String).isNotEmpty
                                    ? c["name"][0]
                                    : "?",
                                style: const TextStyle(fontSize: 18),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    c["name"],
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 6,
                                    children: [
                                      Chip(
                                        label: const Text("In Shop"),
                                        backgroundColor: Colors.green.shade50,
                                        avatar: const Icon(
                                          Icons.check_circle,
                                          size: 18,
                                          color: Colors.green,
                                        ),
                                      ),
                                      Chip(
                                        label: Text("📞 ${c["phone"]}"),
                                        backgroundColor: Colors.grey.shade100,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            ElevatedButton(
                              onPressed: () => finishCustomer(c["id"] as int),
                              child: const Text("Finish"),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),

                  const SizedBox(height: 20),
                  const Divider(),
                  const SizedBox(height: 10),

                  // --------------- waiting ---------------
                  const Text(
                    "Waiting Outside",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),

                  ...waiting.asMap().entries.map((entry) {
                    final i = entry.key;
                    final c = entry.value;

                    return Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 2,
                      margin: const EdgeInsets.symmetric(vertical: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: Colors.teal.shade100,
                              child: Text("${i + 1}"),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    c["name"],
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 6,
                                    children: [
                                      Chip(
                                        label: Text("#${i + 1}"),
                                        backgroundColor: Colors.teal.shade50,
                                      ),
                                      Chip(
                                        label: const Text("Waiting"),
                                        backgroundColor: Colors.orange.shade50,
                                      ),
                                      Chip(
                                        label: Text("📞 ${c["phone"]}"),
                                        backgroundColor: Colors.grey.shade100,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            Column(
                              children: [
                                SizedBox(
                                  height: 36,
                                  child: OutlinedButton(
                                    onPressed: () =>
                                        markArrived(c["id"] as int),
                                    child: const Text("Arrived"),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                SizedBox(
                                  height: 36,
                                  child: OutlinedButton(
                                    onPressed: () => markNoShow(c["id"] as int),
                                    child: const Text("No-show"),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ],
              ),
            ),
    );
  }
}
